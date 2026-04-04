"""Prophet による中長期トレンド予測"""

import logging
import pandas as pd
import numpy as np
from prophet import Prophet

from config import PROPHET_CHANGEPOINT_PRIOR, PROPHET_SEASONALITY_PRIOR

logging.getLogger("prophet").setLevel(logging.WARNING)
logging.getLogger("cmdstanpy").setLevel(logging.WARNING)


class ProphetPredictor:
    def __init__(self, changepoint_prior_scale=None, seasonality_prior_scale=None):
        self.changepoint_prior_scale = changepoint_prior_scale or PROPHET_CHANGEPOINT_PRIOR
        self.seasonality_prior_scale = seasonality_prior_scale or PROPHET_SEASONALITY_PRIOR
        self.model = None
        self._forecast = None

    def train(self, df, regressors=None):
        prophet_df = df[["ds", "y"]].copy().dropna(subset=["y"])
        self.model = Prophet(
            changepoint_prior_scale=self.changepoint_prior_scale,
            seasonality_prior_scale=self.seasonality_prior_scale,
            daily_seasonality=False, weekly_seasonality=True,
            yearly_seasonality=True,
        )
        if regressors:
            for name, series in regressors.items():
                self.model.add_regressor(name)
                prophet_df[name] = series.values[:len(prophet_df)]
        self.model.fit(prophet_df)

    def predict(self, periods, regressors_future=None):
        future = self.model.make_future_dataframe(periods=periods)
        if regressors_future:
            for name, values in regressors_future.items():
                if name in self.model.extra_regressors:
                    hist_len = len(future) - periods
                    train_data = self.model.history[name].values
                    full = np.zeros(len(future))
                    if len(train_data) > 0:
                        full[:len(train_data)] = train_data
                        last_val = train_data[-1]
                    else:
                        last_val = 0.0
                    future_vals = values[:periods] if values else [last_val] * periods
                    full[hist_len:] = future_vals[:len(full) - hist_len]
                    future[name] = full
        self._forecast = self.model.predict(future)
        return self._forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()

    def get_forecast_point(self, periods):
        if self._forecast is None:
            return {"yhat": None, "yhat_lower": None, "yhat_upper": None}
        row = self._forecast.iloc[-periods] if 0 < periods <= len(self._forecast) else self._forecast.iloc[-1]
        return {"yhat": float(row["yhat"]), "yhat_lower": float(row["yhat_lower"]),
                "yhat_upper": float(row["yhat_upper"])}

    def get_future_series(self, periods):
        """未来periods日分の3シナリオ予測系列を返す。"""
        if self._forecast is None:
            self.predict(periods=periods)
        future = self._forecast.tail(periods)[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()
        future = future.rename(columns={"yhat": "standard",
                                         "yhat_upper": "optimistic",
                                         "yhat_lower": "pessimistic"})
        return future

    def get_components(self):
        if self._forecast is None:
            return {}
        return {
            "trend": self._forecast[["ds", "trend"]].copy(),
            "weekly": self._forecast[["ds", "weekly"]].copy() if "weekly" in self._forecast else None,
            "yearly": self._forecast[["ds", "yearly"]].copy() if "yearly" in self._forecast else None,
        }
