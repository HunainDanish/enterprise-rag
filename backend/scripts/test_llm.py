import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.core.llm import llm


def main() -> None:
    response = llm.invoke("Say hello in 5 words")
    print(response.content)


if __name__ == "__main__":
    main()
