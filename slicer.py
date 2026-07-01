import os
import cv2
import numpy as np
from PIL import Image
import logging

logger = logging.getLogger(__name__)


def smart_slice(image_path: str, max_height: int = 1000) -> list:
    """
    智能垂直切片长图。
    使用水平投影法找到最佳切分点（白色间隙/网格线），避免切断文字行。
    支持非 ASCII 路径（如中文路径）。
    """
    try:
        pil_img = Image.open(image_path)
        width, height = pil_img.size

        if height <= max_height:
            return [image_path]

        logger.info(f"Smart slicing: {image_path} ({width}x{height})")

        # 使用 cv2.imdecode 支持非 ASCII 路径
        img_np = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img_np is None:
            logger.warning(f"OpenCV failed to read {image_path}, falling back to standard slicing.")
            return _standard_slice(pil_img, image_path, max_height)

        gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)

        slices = []
        start_y = 0
        search_window = 150  # 在 max_height 上方 150px 范围内搜索最佳切分点

        base_dir = os.path.dirname(image_path)
        base_name, ext = os.path.splitext(os.path.basename(image_path))

        part_idx = 1
        while start_y < height:
            target_end_y = start_y + max_height
            if target_end_y >= height:
                end_y = height
            else:
                # 在 [target_end_y - search_window, target_end_y] 范围内找最佳切分行
                win_start = max(start_y + 100, target_end_y - search_window)
                win_end = target_end_y

                search_area = gray[win_start:win_end, :]
                row_means = np.mean(search_area, axis=1)
                row_vars = np.var(search_area, axis=1)

                # 标准化到 [0, 1]
                mean_norm = row_means / 255.0
                var_norm = row_vars / (255.0 ** 2)

                # 评分：偏好白色行（高均值），惩罚有文字的行列（高方差）
                scores = mean_norm * (1.0 - var_norm * 4.0)

                best_offset = np.argmax(scores)
                end_y = win_start + best_offset

            # 裁剪并保存切片
            slice_np = img_np[start_y:end_y, :]
            slice_path = os.path.join(base_dir, f"{base_name}_part_{part_idx}{ext}")

            is_success, im_buf = cv2.imencode(ext, slice_np)
            if is_success:
                im_buf.tofile(slice_path)
                slices.append(slice_path)
                logger.info(f"Saved slice: {slice_path} (height: {end_y - start_y})")
            else:
                logger.error(f"Failed to save slice: {slice_path}")

            start_y = end_y
            part_idx += 1

        # 清理原图以节省空间
        try:
            os.remove(image_path)
        except Exception as e:
            logger.warning(f"Could not remove original image: {e}")

        return slices
    except Exception as e:
        logger.error(f"Error smart slicing {image_path}: {e}")
        return [image_path]


def _standard_slice(pil_img: Image.Image, image_path: str, max_height: int) -> list:
    """OpenCV 失败时的兜底等分切片"""
    try:
        width, height = pil_img.size
        sliced_paths = []
        num_slices = (height + max_height - 1) // max_height

        base_dir = os.path.dirname(image_path)
        base_name, ext = os.path.splitext(os.path.basename(image_path))

        for i in range(num_slices):
            top = i * max_height
            bottom = min((i + 1) * max_height, height)

            slice_img = pil_img.crop((0, top, width, bottom))
            slice_path = os.path.join(base_dir, f"{base_name}_part_{i + 1}{ext}")
            slice_img.save(slice_path)
            sliced_paths.append(slice_path)

        try:
            os.remove(image_path)
        except Exception:
            pass
        return sliced_paths
    except Exception as e:
        logger.error(f"Standard slice fallback failed: {e}")
        return [image_path]
