import os                   # 操作系统
import shutil               # 文件复制
import argparse             # 脚本参数解析
import subprocess           # 执行命令行命令
from FileList import FileList
import re

def process_file(src_path: str, dst_path: str) -> None:
    """
    处理单个文件，如果是 .ts 文件，则使用 ffmpeg 转换为 .mp4，否则直接复制。

    Args:
        src_path (str): 源文件路径。
        dst_path (str): 目标文件路径。
    """
    if src_path.lower().endswith(".ts") and dst_path.lower().endswith(".ts"):
        name, ext = os.path.splitext(dst_path)
        dst_path = name + ".mp4"
        try:
            subprocess.run(["ffmpeg", "-i", src_path, "-c", "copy", dst_path], check=True, capture_output=True)
            print(f"已使用 ffmpeg 转换: {src_path} -> {dst_path}")
        except subprocess.CalledProcessError as e:
            print(f"ffmpeg 转换失败: {src_path} -> {dst_path}, 错误信息: {e}")
    else:
        shutil.copy2(src_path, dst_path)
        print(f"已复制: {src_path} -> {dst_path}")

def batch_rename(input_folder: str, output_folder: str, prefix: str = "", suffix: str = "", sort_method: str = "name", test: bool = False) -> None:
    """
    批量重命名指定目录下的文件，并根据文件类型进行处理。

    Args:
        input_folder (str): 包含待处理文件的目录。
        output_folder (str): 处理后文件存放的目录。
        prefix (str): 输出文件名的前缀。
        sort_method (str): 排序方法 (name, size, date, duplicate)
        test (bool): 是否为测试模式
    """
    # 根据要求的排序方法对文件列表进行排序
    file_list = FileList(input_folder)
    if sort_method == "name":
        file_list.sort_by_name()
    elif sort_method == "size":
        file_list.sort_by_size()
    elif sort_method == "date":
        file_list.sort_by_date()
    elif sort_method == "number":
        file_list.sort_by_number()
    # elif sort_method == "duplicate":
    #     file_list.duplicate_sort()
    else:
        print("无效的排序方法，使用默认排序（按文件名）")
        file_list.sort_by_name()

    # 测试模式不进行实际操作
    if test:
        print("测试模式：仅打印排序后的文件列表供顺序检查")
        print(f"将执行拷贝：{input_folder} -> {output_folder}")
        print()
        file_list.print()
        return

    # 遍历处理所有源文件，idx 从 1 开始
    os.makedirs(output_folder, exist_ok=True)
    for idx, src_name in enumerate(file_list, 1):
        name, ext = os.path.splitext(src_name)
        # 提取 name 开头的首段（支持可选括号或中括号），并将该首段从 name 中移除
        # 然后保留该首段中 "非数字且非空白" 的字符，加入到目标名中
        m = re.match(r"^\s*(?:\(|\[)?(\d+)(?:\)|\])?[\s\-_.]*", name)
        if m:
            seg = m.group(0)
            name = name[m.end():]
            keep = re.sub(r"[\d\s]+", "", seg)
        else:
            keep = ""

        # 将提取到的保留字符加入到 dst_name 中，位于 suffix 与 ext 之间
        if keep:
            dst_name = f"{prefix}{idx:03d}{suffix}{keep}{ext}"
        else:
            dst_name = f"{prefix}{idx:03d}{suffix}{ext}"
        src_path = os.path.join(input_folder, src_name)   # 原文件完整路径
        dst_path = os.path.join(output_folder, dst_name)  # 新文件完整路径
        process_file(src_path, dst_path)  # 调用处理文件的函数

if __name__ == "__main__":
    # 创建命令行参数解析器，添加输入输出目录参数
    parser = argparse.ArgumentParser(description="批量重命名文件为“第N集”")
    parser.add_argument("-i", "--input", required=True, help="输入目录")
    parser.add_argument("-o", "--output", required=True, help="输出目录")
    parser.add_argument("-p", "--prefix", default="", help="输出文件名的前缀")
    parser.add_argument("--suffix", default="", help="输出文件名的后缀")
    parser.add_argument("-s", "--sort", default="name",
                        choices=["name", "size", "date", "number"],
                        help="排序方法 (name, size, date, number)")
    parser.add_argument("-t", "--test", action="store_true",
                        help="测试模式：仅打印排序后的文件列表")
    args = parser.parse_args()

    batch_rename(args.input, args.output, args.prefix, args.suffix, args.sort, args.test)  # 调用批量重命名函数

