from pydantic_settings import BaseSettings


class settings(BaseSettings):

    # DataBase Settings
    DATABASE_URL: str 
    ECHO: bool = False



    class Config:
        env_file = ".env"

