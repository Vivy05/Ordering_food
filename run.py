import uvicorn
import logging
logging.basicConfig(level=logging.INFO)


def main():
    try:
        uvicorn.run("api.main:app", host="127.0.0.1", port=8000, log_level="info")
    except KeyboardInterrupt as e:
        logging.error(f"启动uvicorn失败,问题：{e}")


if __name__ == "__main__":
    main()
