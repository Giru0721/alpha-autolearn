"""Prophet用 CmdStan 初回セットアップスクリプト"""

import sys


def main():
    print("=" * 50)
    print("  CmdStan セットアップ")
    print("  Prophet の初回起動に必要です")
    print("=" * 50)
    print()

    try:
        import cmdstanpy
        if cmdstanpy.cmdstan_path():
            print(f"CmdStan は既にインストール済みです: {cmdstanpy.cmdstan_path()}")
            return
    except Exception:
        pass

    print("CmdStan をインストール中... (数分かかります)")
    try:
        import cmdstanpy
        cmdstanpy.install_cmdstan()
        print()
        print("CmdStan のインストールが完了しました!")
    except Exception as e:
        print(f"エラー: {e}")
        print()
        print("手動インストール:")
        print("  pip install cmdstanpy")
        print("  python -m cmdstanpy.install_cmdstan")
        sys.exit(1)


if __name__ == "__main__":
    main()
