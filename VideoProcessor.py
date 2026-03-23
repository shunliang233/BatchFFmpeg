# -*- coding: utf-8 -*-
"""
VideoProcessor - 视频批处理工具

功能：
- 批量转换 TS 文件为 MP4
- 合并序列号连续的视频文件
- 自动检测并验证文件序列号

Last Modified: 2026-03-14
"""

import re                     # 正则表达式
from pathlib import Path      # 路径处理
from typing import List, Dict # 类型提示
from enum import Enum         # 枚举类型
import argparse               # 脚本参数解析

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
        print(f"检测到需要合并视频: {self._video_merge}\n")
    
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
        file_number_pairs: List[tuple[Path, int]] = []
        for in_file in self._file_list:
            matches = re.search(pattern, in_file.stem)
            if not matches:
                raise ValueError(f"文件名不匹配模式 {pattern}: {in_file.name}")
            sequence = int(matches.group(1))
            file_number_pairs.append((in_file, sequence))
        file_number_pairs.sort(key=lambda x: x[1])
        # 计算需要补零的位数
        total = len(file_number_pairs)
        width = len(str(total))
        # 生成新文件名映射
        for idx, (in_file, seq_num) in enumerate(file_number_pairs, start=1):
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
    
    def _validate_inputs(self, in_files: List[Path]) -> None:
        """拼接前验证每个文件的有效性及流参数一致性

        Args:
            in_files: 待拼接文件列表
        Raises:
            ValueError: 文件损坏、缺少视频流或参数不一致时抛出
        """
        import subprocess
        import json

        streams_list: List[tuple[Path, list[dict]]] = []
        for in_file in in_files:
            result = subprocess.run(
                ["ffprobe", "-v", "error",
                 "-show_streams", "-print_format", "json",
                 str(in_file)],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                raise ValueError(
                    f"文件无效或损坏: {in_file.name}\n{result.stderr.strip()}"
                )
            info = json.loads(result.stdout)
            streams: list[dict] = info.get("streams", [])
            if not streams:
                raise ValueError(f"文件没有有效的流: {in_file.name}")
            streams_list.append((in_file, streams))

        def get_stream(streams: list[dict], codec_type: str) -> dict | None:
            """从流列表中找出指定类型（视频或音频）的第一条流，找不到就返回 None。"""
            return next(
                (s for s in streams if s.get("codec_type") == codec_type),
                None)

        ref_file, ref_streams = streams_list[0]
        ref_video = get_stream(ref_streams, "video")
        ref_audio = get_stream(ref_streams, "audio")
        if ref_video is None:
            raise ValueError(f"文件缺少视频流: {ref_file.name}")
        if ref_audio is None:
            raise ValueError(f"文件缺少音频流: {ref_file.name}")

        for in_file, streams in streams_list[1:]:
            video = get_stream(streams, "video")
            audio = get_stream(streams, "audio")

            # 检查视频流
            if video is None:
                raise ValueError(f"文件缺少视频流: {in_file.name}")
            if video.get("codec_name") != ref_video.get("codec_name"):
                raise ValueError(
                    f"视频编解码器不匹配:\n"
                    f"  {ref_file.name}: {ref_video.get('codec_name')}\n"
                    f"  {in_file.name}: {video.get('codec_name')}"
                )
            if (video.get("width") != ref_video.get("width") or
                    video.get("height") != ref_video.get("height")):
                raise ValueError(
                    f"视频分辨率不匹配:\n"
                    f"  {ref_file.name}: "
                    f"{ref_video.get('width')}x{ref_video.get('height')}\n"
                    f"  {in_file.name}: "
                    f"{video.get('width')}x{video.get('height')}"
                )

            # 检查音频流
            if audio is None:
                raise ValueError(f"文件缺少音频流: {in_file.name}")
            if audio.get("codec_name") != ref_audio.get("codec_name"):
                raise ValueError(
                    f"音频编解码器不匹配:\n"
                    f"  {ref_file.name}: {ref_audio.get('codec_name')}\n"
                    f"  {in_file.name}: {audio.get('codec_name')}"
                )
            if audio.get("sample_rate") != ref_audio.get("sample_rate"):
                raise ValueError(
                    f"音频采样率不匹配:\n"
                    f"  {ref_file.name}: {ref_audio.get('sample_rate')} Hz\n"
                    f"  {in_file.name}: {audio.get('sample_rate')} Hz"
                )
            if audio.get("channels") != ref_audio.get("channels"):
                raise ValueError(
                    f"音频声道数不匹配:\n"
                    f"  {ref_file.name}: {ref_audio.get('channels')} 声道\n"
                    f"  {in_file.name}: {audio.get('channels')} 声道"
                )
            if audio.get("profile") != ref_audio.get("profile"):
                raise ValueError(
                    f"音频编解码器 Profile 不匹配:\n"
                    f"  {ref_file.name}: {ref_audio.get('profile')}\n"
                    f"  {in_file.name}: {audio.get('profile')}"
                )

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
                    print(f"已复制: -> {out_file.name}")
            else:
                # 多个输入文件，合并为一个输出文件
                concat_file = self.tmp_folder / (out_file.stem + "_concat.txt")
                with concat_file.open("w", encoding="utf-8") as f:
                    for in_file in in_files:
                        f.write(f"file '{in_file.as_posix()}'\n")
                try:
                    self._validate_inputs(in_files)
                except ValueError as e:
                    print(f"验证失败，跳过合并 {out_file.name}: {e}")
                    dest = self.out_folder / concat_file.name
                    shutil.copy2(concat_file, dest)
                    concat_file.unlink(missing_ok=True)
                    continue
                try:
                    subprocess.run(
                        ["ffmpeg", "-f", "concat", "-safe", "0", "-i", str(concat_file),
                         "-c", "copy", str(out_file)],
                        check=True, capture_output=True
                    )
                    print(f"已合并: -> {out_file.name}")
                except subprocess.CalledProcessError as e:
                    print(f"合并失败: {[f.name for f in in_files]}, 错误信息: {e}")
                finally:
                    concat_file.unlink(missing_ok=True)
        self.tmp_folder.rmdir()

    def print(self) -> None:
        """展示将要进行的文件转换操作"""
        if not self._file_map:
            print("[没有文件需要处理]")
            return
        
        # 计算最长输入文件名宽度，用于对齐 -->
        max_width = max(
            max(len(f.name) for f in in_files)
            for in_files in self._file_map.values()
        )
        
        for out_file, in_files in self._file_map.items():
            if len(in_files) == 1:
                print(f"{in_files[0].name:<{max_width}}  -->  {out_file.name}")
            else:
                mid = len(in_files) // 2
                for i, in_file in enumerate(in_files):
                    if i == mid:
                        arrow = f"  -->  {out_file.name}"
                    elif i == 0:
                        arrow = "  \\"
                    elif i == len(in_files) - 1:
                        arrow = "  /"
                    else:
                        arrow = "  |"
                    print(f"{in_file.name:<{max_width}}{arrow}")
            print()


# TODO: Check video audio alignment of output file.
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
    parser.add_argument("-t", "--test", action="store_true",
                        help="测试模式：仅打印排序后的文件列表")
    args = parser.parse_args()
    
    processor = VideoProcessor(args.input, args.output,
                               Mode(args.mode), args.pattern)
    if args.test:
        processor.print()
    else:
        processor.processor()