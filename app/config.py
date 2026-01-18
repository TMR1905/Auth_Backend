from pydantic_settings import BaseSettings


class settings(BaseSettings):

    # DataBase Settings
    DATABASE_URL: str 
    



    class Config:
        env_file = ".env"