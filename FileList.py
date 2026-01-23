import os                           # 操作系统
import re                           # 正则表达式
from pathlib import Path            # 路径处理
from typing import List, Tuple, Dict, Iterator   # 类型提示

class FileList:
    """表示文件列表的类，提供文件列表的获取、排序等功能"""

    def __init__(self, input_folder: str):
        """构造函数：读取输入目录，初始化文件列表"""
        self.input_folder = Path(input_folder)
        if not self.input_folder.exists():
            raise FileNotFoundError(f"目录不存在: {input_folder}")
        if not self.input_folder.is_dir():
            raise NotADirectoryError(f"不是目录: {input_folder}")
        self._file_list: List[Path] = self._get_file_list()
        self._file_group: Dict[str, Tuple[Path, ...]] = self._group_file()
    def _get_file_list(self) -> List[Path]:
        """从输入目录获取文件列表，并排除子目录"""
        return [f for f in self.input_folder.iterdir() if f.is_file()]
    def _group_file(self) -> Dict[str, Tuple[Path, ...]]:
        """将文件按文件名分组，只有最后的序列号不同的文件分到一组"""
        pattern_dict = {}
        for f in self._file_list:
            pattern = re.sub(r"-\d+$", "", f.stem) + f.suffix
            if pattern not in pattern_dict:
                pattern_dict[pattern] = []
            pattern_dict[pattern].append(f)
        return {pattern: tuple(files) for pattern, files in pattern_dict.items()}

    # 按不同方式排序的方法
    def sort_by_duplicate(self) -> None:
        """按文件名最后的括号内数字排序"""
        def get_number(file_path: Path) -> int:
            """提取文件名最后的括号内数字"""
            matches = re.search(r"\((\d+)\)$", file_path.stem)
            if not matches:
                return 0
            return int(matches.group(1))
        self._file_list.sort(key=get_number)
    def sort_by_name(self) -> None:
        """按文件名排序"""
        self._file_list.sort()
    def sort_by_size(self) -> None:
        """按文件大小排序"""
        self._file_list.sort(key=lambda f: f.stat().st_size)
    def sort_by_date(self) -> None:
        """按修改日期排序"""
        self._file_list.sort(key=lambda f: f.stat().st_mtime)

    # 格式化输出文件列表
    def print(self, n: int = 5) -> None:
        """格式化输出文件列表，每行 n 个，纵向对齐"""
        if not self._file_list:
            print("[空列表]")
            return
        maxlen = max(len(f.name) for f in self._file_list)
        for i in range(0, len(self._file_list), n):
            row = self._file_list[i:i+n]
            print('  '.join(f.name.ljust(maxlen) for f in row))

    # 模拟列表接口
    def __len__(self) -> int:
        """返回文件数量"""
        return len(self._file_list)
    def __getitem__(self, index: int) -> Path:
        """获取指定索引的文件路径"""
        return self._file_list[index]
    def __iter__(self) -> Iterator[Path]:
        """返回迭代器"""
        return iter(self._file_list)
    def __contains__(self, item: str | Path) -> bool:
        """检查是否包含指定文件"""
        path_item = Path(item) if isinstance(item, str) else item
        return path_item in self._file_list
    def append(self, item: str | Path) -> None:
        """添加文件"""
        path_item = Path(item) if isinstance(item, str) else item
        self._file_list.append(path_item)
    def extend(self, items: List[str | Path]) -> None:
        """扩展文件列表"""
        path_items = [Path(item) if isinstance(item, str) else item for item in items]
        self._file_list.extend(path_items)
    def insert(self, index: int, item: str | Path) -> None:
        """插入文件"""
        path_item = Path(item) if isinstance(item, str) else item
        self._file_list.insert(index, path_item)
    def remove(self, item: str | Path) -> None:
        """移除文件"""
        path_item = Path(item) if isinstance(item, str) else item
        self._file_list.remove(path_item)
    def pop(self, index: int = -1) -> Path:
        """弹出文件"""
        return self._file_list.pop(index)
    def clear(self) -> None:
        """清空文件列表"""
        self._file_list.clear()
    def copy(self) -> List[Path]:
        """复制文件列表"""
        return self._file_list.copy()
    def __str__(self) -> str:
        """返回文件列表的字符串表示"""
        return str(self._file_list)
