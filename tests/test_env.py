import os

from bot.env import load_env


def test_load_env_reads_file(tmp_path):
    key = "MM_DOTENV_TEST"
    os.environ.pop(key, None)
    try:
        p = tmp_path / ".env"
        p.write_text(f"{key}=hello\n", encoding="utf-8")
        load_env(str(p))
        assert os.environ[key] == "hello"
    finally:
        os.environ.pop(key, None)


def test_load_env_missing_file_is_noop(tmp_path):
    key = "MM_DOTENV_MISSING"
    os.environ.pop(key, None)
    load_env(str(tmp_path / "nope.env"))  # 파일 없어도 예외 없이 통과
    assert key not in os.environ


def test_existing_env_var_is_not_overridden(tmp_path):
    key = "MM_DOTENV_KEEP"
    os.environ[key] = "original"
    try:
        p = tmp_path / ".env"
        p.write_text(f"{key}=fromfile\n", encoding="utf-8")
        load_env(str(p))
        assert os.environ[key] == "original"  # 기존 환경변수 우선
    finally:
        os.environ.pop(key, None)
