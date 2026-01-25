# -*- coding: utf-8 -*-
"""
VideoProcessor - 视频批处理工具

功能：
- 批量转换 TS 文件为 MP4
- 合并序列号连续的视频文件
- 自动检测并验证文件序列号

Last Modified: 2026-01-25
"""

import re                           # 正则表达式
from pathlib import Path            # 路径处理
from typing import List, Dict, Iterator   # 类型提示
from enum import Enum               # 枚举类型
import argparse             # 脚本参数解析

class Mode(Enum):
    MERGE = "merge"      # 合并模式
    RENAME = "rename"    # 重命名模式

class VideoProcessor:
    """处理输入目录中的视频，存储到输出目录"""

    def __init__(self, in_folder_str: str, out_folder_str: str,
                 mode: Mode, pattern: str):
        """构造函数：读取输入目录，初始化文件列表
        
        Args:
            in_folder_str: 输入目录路径
            out_folder_str: 输出目录路径
            mode: 处理模式
            pattern: 重命名模式的正则表达式（仅在 RENAME 模式下使用）
        """
        
        # 初始化输入输出目录
        self.in_folder = Path(in_folder_str)
        self.out_folder = Path(out_folder_str)
        self.tmp_folder = self.in_folder / "tmp"
        if not self.in_folder.exists():
            raise FileNotFoundError(f"目录不存在: {in_folder_str}")
        if not self.in_folder.is_dir():
            raise NotADirectoryError(f"不是目录: {in_folder_str}")
        if self.out_folder.exists():
            if not self.out_folder.is_dir():
                raise NotADirectoryError(f"输出路径不是目录: {out_folder_str}")
            if any(self.out_folder.iterdir()):
                raise FileExistsError(f"输出目录不为空: {out_folder_str}")
        
        # 读取输入目录下的所有文件，构建文件列表和映射
        self._file_list: List[Path] = []
        for in_file in self.in_folder.iterdir():
            if not in_file.is_file():
                continue
            if in_file.suffix.lower() != ".mp4" and \
               in_file.suffix.lower() != ".ts":
                continue
            self._file_list.append(in_file)
        self._file_list.sort()
        
        # 根据模式选择构建文件映射
        self._file_map: Dict[Path, List[Path]] = {}
        if mode == Mode.MERGE:
            self._merge()
        elif mode == Mode.RENAME:
            self._rename(pattern)
        
        # 检测 processor 的处理内容
        self._video_merge: bool = self._detect_video_merge()
        print(f"检测到需要合并视频: {self._video_merge}")
    
    def _merge(self) -> None:
        """合并视频文件"""
        for in_file in self._file_list:
            pattern = re.sub(r"-\d+$", "", in_file.stem) + ".mp4"
            out_file = self.out_folder / pattern
            if out_file not in self._file_map:
                self._file_map[out_file] = []
            self._file_map[out_file].append(in_file)
    
    def _rename(self, pattern: str) -> None:
        """根据给定的模式重命名文件
        
        Args:
            pattern: 正则表达式，用于捕获文件名中的数字部分
        """
        # 提取文件中对应的数字进行排序
        file_number_pairs = []
        for in_file in self._file_list:
            matches = re.search(pattern, in_file.stem)
            if not matches:
                raise ValueError(f"文件名不匹配模式 {pattern}: {in_file.name}")
            number = int(matches.group(1))
            file_number_pairs.append((in_file, number))
        file_number_pairs.sort(key=lambda x: x[1])
        # 计算需要补零的位数
        total = len(file_number_pairs)
        width = len(str(total))
        # 生成新文件名映射
        for idx, (in_file, old_number) in enumerate(file_number_pairs, start=1):
            new_number = str(idx).zfill(width)
            new_stem = re.sub(pattern, new_number, in_file.stem, count=1)
            out_file = self.out_folder / (new_stem + ".mp4")
            self._file_map[out_file] = [in_file]
    
    def _detect_video_merge(self) -> bool:
        """检测是否需要合并视频文件，并验证序列号的连续性"""
        has_merge = False
        for out_file, in_files in self._file_map.items():
            if len(in_files) > 1:
                has_merge = True
                # 提取每个文件的序列号
                numbers = []
                for in_file in in_files:
                    matches = re.search(r"-(\d+)$", in_file.stem)
                    if not matches:
                        raise ValueError(f"文件名缺少序列号: {in_file.name}")
                    numbers.append(int(matches.group(1)))
                # 检查序列号是否从1开始且连续
                numbers.sort()
                expected = list(range(1, len(numbers) + 1))
                if numbers != expected:
                    raise ValueError(
                        f"文件序列号不连续或不从1开始: {out_file.name}\n"
                        f"期望: {expected}, 实际: {numbers}"
                    )
        return has_merge
    
    def processor(self) -> None:
        """处理视频文件，合并或转换后存储到输出目录"""
        import subprocess
        import shutil

        # 处理每个输出文件
        self.out_folder.mkdir(parents=True, exist_ok=True)
        self.tmp_folder.mkdir(parents=True, exist_ok=True)
        for out_file, in_files in self._file_map.items():
            if len(in_files) == 1:
                # 仅有一个输入文件，直接转换或复制
                in_file = in_files[0]
                if in_file.suffix.lower() == ".ts":
                    try:
                        subprocess.run(
                            ["ffmpeg", "-i", str(in_file), "-c", "copy", str(out_file)],
                            check=True, capture_output=True
                        )
                        print(f"已转换: {in_file.name} -> {out_file.name}")
                    except subprocess.CalledProcessError as e:
                        print(f"转换失败: {in_file.name}, 错误信息: {e}")
                else:
                    shutil.copy2(in_file, out_file)
                    print(f"已复制: {in_file.name} -> {out_file.name}")
            else:
                # 多个输入文件，合并为一个输出文件
                concat_file = self.tmp_folder / (out_file.stem + "_concat.txt")
                with concat_file.open("w", encoding="utf-8") as f:
                    for in_file in in_files:
                        f.write(f"file '{in_file.as_posix()}'\n")
                try:
                    subprocess.run(
                        ["ffmpeg", "-f", "concat", "-safe", "0", "-i", str(concat_file),
                         "-c", "copy", str(out_file)],
                        check=True, capture_output=True
                    )
                    print(f"已合并: {[f.name for f in in_files]} -> {out_file.name}")
                except subprocess.CalledProcessError as e:
                    print(f"合并失败: {[f.name for f in in_files]}, 错误信息: {e}")
                finally:
                    concat_file.unlink(missing_ok=True)
    

    # # 按不同方式排序的方法
    # def sort_by_duplicate(self) -> None:
    #     """按文件名最后的括号内数字排序"""
    #     def get_number(file_path: Path) -> int:
    #         """提取文件名最后的括号内数字"""
    #         matches = re.search(r"\((\d+)\)$", file_path.stem)
    #         if not matches:
    #             return 0
    #         return int(matches.group(1))
    #     self._file_list.sort(key=get_number)
    # def sort_by_name(self) -> None:
    #     """按文件名排序"""
    #     self._file_list.sort()
    # def sort_by_size(self) -> None:
    #     """按文件大小排序"""
    #     self._file_list.sort(key=lambda f: f.stat().st_size)
    # def sort_by_date(self) -> None:
    #     """按修改日期排序"""
    #     self._file_list.sort(key=lambda f: f.stat().st_mtime)

    # 格式化输出文件列表
    def print(self, n: int = 5) -> None:
        """展示将要进行的文件转换操作"""
        if not self._file_map:
            print("[没有文件需要处理]")
            return
        
        for out_file, in_files in self._file_map.items():
            in_names = ", ".join(f.name for f in in_files)
            print(f"{in_names} --> {out_file.name}")
        # """格式化输出文件列表，每行 n 个，纵向对齐"""
        # if not self._file_list:
        #     print("[空列表]")
        #     return
        # maxlen = max(len(f.name) for f in self._file_list)
        # for i in range(0, len(self._file_list), n):
        #     row = self._file_list[i:i+n]
        #     print('  '.join(f.name.ljust(maxlen) for f in row))


if __name__ == "__main__":
    # 创建命令行参数解析器，添加输入输出目录参数
    parser = argparse.ArgumentParser(description="批量处理视频文件")
    parser.add_argument("-i", "--input", required=True, help="输入目录")
    parser.add_argument("-o", "--output", required=True, help="输出目录")
    parser.add_argument("-m", "--mode", required=True,
                        choices=[m.value for m in Mode],
                        help="处理模式")
    parser.add_argument("--pattern", default=r"(\d+)",
                        help="重命名模式的正则表达式（仅在 rename 模式下使用）")
    # parser.add_argument("--prefix", default="", help="输出文件名的前缀")
    # parser.add_argument("--suffix", default="", help="输出文件名的后缀")
    # parser.add_argument("-s", "--sort", default="name",
    #                     choices=["name", "size", "date", "number"],
    #                     help="排序方法 (name, size, date, number)")
    parser.add_argument("-t", "--test", action="store_true",
                        help="测试模式：仅打印排序后的文件列表")
    args = parser.parse_args()
    
    processor = VideoProcessor(args.input, args.output,
                               Mode(args.mode), args.pattern)
    if args.test:
        processor.print()
    else:
        processor.processor()