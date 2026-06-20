import argparse
import http.server
import itertools
import os
import shutil
import subprocess

from modules.dependency.providers import Provider
from modules.domain.models.markdown import NamedMarkdown
from modules.domain.models.page import PageBuilder, Template
from modules.domain.models.path import Path
from modules.domain.models.scenario import ScenarioProperty
from modules.libraries.loggers import ILogger


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["build", "pdf"])
    parser.add_argument("-t", "--target", nargs="?", type=str)
    parser.add_argument("-a", "--author", nargs="?", type=str)
    parser.add_argument("-n", "--name", nargs="?", type=str)
    args = parser.parse_args()
    match args.command:
        case "build":
            return handle_build(args)
        case "pdf":
            return handle_pdf(args)


def handle_build(args: argparse.Namespace) -> None:
    files = get_markdown_files(args.target)
    if not files:
        raise RuntimeError(f"シナリオファイルが見つかりません: {args.target}")
    verified = verify_markdown_files(files)
    if not verified:
        raise RuntimeError("シナリオファイルに定義不足があるので変換できません")

    logger = Provider[ILogger]()

    # 現在時刻に応じた新しい出力ディレクトリ作成する
    output_dir = os.path.join("output", f"{os.path.basename(args.target)}")
    shutil.rmtree(output_dir, ignore_errors=True)
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"出力ディレクトリ: {output_dir} を作成しました")

    # すべてのMarkdown以外のファイルをコピーする
    for file in get_resource_files(args.target):
        shutil.copy(str(file), output_dir)
        logger.info(f"リソースファイル: {str(file)} をコピーしました")

    # 設定ファイルからタイトルを取得する。存在しなければフォルダ名とする
    output_property = os.path.join(output_dir, "properties.json")
    try:
        property = ScenarioProperty.from_path(output_property)
    except FileNotFoundError:
        property = ScenarioProperty(title=os.path.basename(args.target), author="")

    # MarkdownファイルはHTMLとして連結する
    html = (
        PageBuilder()
        .set_title(property.title)
        .set_template(Template.from_path("modules/views/html/template.html"))
        .build(files)
    )
    with open(os.path.join(output_dir, "output.html"), "w", encoding="utf-8") as file:
        file.write(html)
        logger.info("MarkdownをHTMLに変換しました")
    server = http.server.ThreadingHTTPServer(
        server_address=("", 8000),
        RequestHandlerClass=http.server.SimpleHTTPRequestHandler,
    )
    url = f"http://localhost:8000/{output_dir}/output.html"
    logger.info(f"\u001b]8;;{url}\u001b\\{url}\u001b]8;;\u001b\\")
    logger.info("でサーバーを開始しました。終了するにはCtrl-Cを押してください")
    server.serve_forever()


def handle_pdf(args: argparse.Namespace) -> None:
    output_dir = os.path.join("output", f"{os.path.basename(args.target)}")
    output_property = os.path.join(output_dir, "properties.json")
    output_path = os.path.join(output_dir, "output.pdf")
    output_fixed_path = os.path.join(output_dir, "output-fixed.pdf")
    try:
        os.remove(output_fixed_path)
    except FileNotFoundError:
        pass
    try:
        property = ScenarioProperty.from_path(output_property)
        subprocess.run(
            [
                "exiftool",
                "-all=",
                f"-Title={property.title}",
                f"-Author={property.author}",
                output_path,
                "-o",
                output_fixed_path,
            ]
        )
        subprocess.run(["qpdf", "--linearize", "--replace-input", output_fixed_path])
    except Exception:
        pass


def get_resource_files(target: str) -> list[Path]:
    files: list[Path] = []
    for dirpath, _, filenames in os.walk(target):
        for filename in filenames:
            if not filename.endswith(".md"):
                files.append(Path(os.path.join(dirpath, filename)))
    return files


def get_markdown_files(target: str) -> list[NamedMarkdown]:
    # .mdファイルをすべて取得してフロントマターと内容に分割する
    files: list[NamedMarkdown] = []
    for dirpath, _, filenames in os.walk(target):
        for filename in filenames:
            if filename.endswith(".md"):
                file = os.path.join(dirpath, filename)
                with open(file, encoding="utf-8") as fp:
                    files.append(NamedMarkdown.parse_named(filename, fp.read()))
    return files


def verify_markdown_files(files: list[NamedMarkdown]) -> bool:
    # すべてのtitleとindexが設定されているか確認する
    logger = Provider[ILogger]()
    verified = 0
    for file in files:
        is_ok = True
        if not file.title:
            logger.warning(f"フロントマターに`title`が指定されていません: {file.name}")
            is_ok = False
        if file.index < 0:
            logger.warning(f"フロントマターに`index`が指定されていません: {file.name}")
            is_ok = False
        if is_ok:
            verified += 1
    if verified != len(files):
        return False

    unique_index = 0
    for _, f in itertools.groupby(files, lambda x: x.index):
        same_index_files = list(f)
        if len(same_index_files) > 1:
            names = ", ".join(x.name for x in same_index_files)
            logger.warning(f"同じ`index`が指定されているファイルが存在します: {names}")
        else:
            unique_index += 1
    if unique_index != len(files):
        return False

    return True


if __name__ == "__main__":
    main()
