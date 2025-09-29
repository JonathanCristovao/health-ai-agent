def load_text(file_path: str) -> str:
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def save_text(file_path: str, content: str):
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
