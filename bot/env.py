from dotenv import load_dotenv


def load_env(path: str = ".env") -> None:
    """있으면 .env 파일을 읽어 환경변수로 로드한다.
    override=False: 이미 설정된 환경변수가 .env보다 우선한다.
    파일이 없으면 아무 일도 하지 않는다.
    """
    load_dotenv(path, override=False)
