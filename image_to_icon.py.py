import sys
import os
from PIL import Image
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
							 QHBoxLayout, QPushButton, QLabel, QFileDialog,
							 QComboBox, QSpinBox, QGroupBox, QMessageBox,
							 QProgressBar)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QDragEnterEvent, QDropEvent


class ConvertThread(QThread):
	"""转换线程，避免界面卡顿"""
	progress = pyqtSignal(int)
	finished = pyqtSignal(bool, str)

	def __init__(self, input_path, output_path, sizes):
		super().__init__()
		self.input_path = input_path
		self.output_path = output_path
		self.sizes = sizes

	def run(self):
		try:
			# 打开图片
			img = Image.open(self.input_path)

			# 转换为RGBA模式（支持透明）
			if img.mode != 'RGBA':
				img = img.convert('RGBA')

			# 生成多种尺寸的图标
			icons = []
			for i, size in enumerate(self.sizes):
				# 调整尺寸，保持宽高比
				img_resized = img.copy()
				img_resized.thumbnail((size, size), Image.Resampling.LANCZOS)

				# 创建正方形画布（透明背景）
				square_img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
				offset = ((size - img_resized.width) // 2,
						  (size - img_resized.height) // 2)
				square_img.paste(img_resized, offset)

				icons.append(square_img)
				self.progress.emit(int((i + 1) / len(self.sizes) * 100))

			# 保存为ICO文件
			if len(icons) > 1:
				icons[0].save(self.output_path, format='ICO', sizes=[(s, s) for s in self.sizes],
							  append_images=icons[1:])
			else:
				icons[0].save(self.output_path, format='ICO')

			self.finished.emit(True, f"转换成功！\n保存位置：{self.output_path}")
		except Exception as e:
			self.finished.emit(False, f"转换失败：{str(e)}")


class ImageToIconTool(QMainWindow):
	def __init__(self):
		super().__init__()
		self.input_image_path = None
		self.init_ui()

	def init_ui(self):
		"""初始化用户界面"""
		self.setWindowTitle("图片转ICO工具")
		self.setGeometry(300, 300, 600, 500)

		# 设置窗口支持拖放
		self.setAcceptDrops(True)

		# 中央部件
		central_widget = QWidget()
		self.setCentralWidget(central_widget)

		# 主布局
		main_layout = QVBoxLayout(central_widget)

		# 拖放区域
		self.drop_label = QLabel()
		self.drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
		self.drop_label.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 10px;
                padding: 40px;
                background-color: #f8f9fa;
                font-size: 14px;
            }
            QLabel:hover {
                border-color: #0078d4;
                background-color: #e8f0fe;
            }
        """)
		self.drop_label.setText("拖拽图片到这里\n或点击下方按钮选择图片")
		self.drop_label.setMinimumHeight(200)
		main_layout.addWidget(self.drop_label)

		# 图片预览区域
		self.preview_label = QLabel()
		self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
		self.preview_label.setStyleSheet("border: 1px solid #ccc; padding: 10px;")
		self.preview_label.setMinimumHeight(150)
		self.preview_label.hide()
		main_layout.addWidget(self.preview_label)

		# 控制面板
		control_group = QGroupBox("转换设置")
		control_layout = QVBoxLayout()

		# 尺寸选择
		size_layout = QHBoxLayout()
		size_layout.addWidget(QLabel("图标尺寸（多个尺寸用逗号分隔）："))
		self.size_input = QSpinBox()
		self.size_input.setRange(16, 256)
		self.size_input.setValue(256)
		size_layout.addWidget(self.size_input)
		size_layout.addWidget(QLabel("px"))
		size_layout.addStretch()

		self.multi_size_btn = QPushButton("添加尺寸")
		self.multi_size_btn.clicked.connect(self.add_size)
		size_layout.addWidget(self.multi_size_btn)

		control_layout.addLayout(size_layout)

		# 尺寸列表
		self.size_list_label = QLabel("当前尺寸列表：256x256")
		self.size_list_label.setStyleSheet("color: #666; font-size: 12px;")
		control_layout.addWidget(self.size_list_label)

		self.sizes = [256]  # 默认尺寸列表

		# 按钮布局
		button_layout = QHBoxLayout()

		self.select_btn = QPushButton("选择图片")
		self.select_btn.clicked.connect(self.select_image)
		button_layout.addWidget(self.select_btn)

		self.convert_btn = QPushButton("转换为ICO")
		self.convert_btn.clicked.connect(self.convert_to_icon)
		self.convert_btn.setEnabled(False)
		self.convert_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                font-weight: bold;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #005a9e;
            }
            QPushButton:disabled {
                background-color: #ccc;
            }
        """)
		button_layout.addWidget(self.convert_btn)

		self.clear_btn = QPushButton("清除")
		self.clear_btn.clicked.connect(self.clear_image)
		button_layout.addWidget(self.clear_btn)

		control_layout.addLayout(button_layout)

		# 进度条
		self.progress_bar = QProgressBar()
		self.progress_bar.hide()
		control_layout.addWidget(self.progress_bar)

		control_group.setLayout(control_layout)
		main_layout.addWidget(control_group)

		# 状态栏
		self.statusBar().showMessage("就绪")

	def add_size(self):
		"""添加图标尺寸"""
		new_size = self.size_input.value()
		if new_size not in self.sizes:
			self.sizes.append(new_size)
			self.sizes.sort()
			size_text = "、".join([f"{s}x{s}" for s in self.sizes])
			self.size_list_label.setText(f"当前尺寸列表：{size_text}")
			self.statusBar().showMessage(f"已添加尺寸 {new_size}x{new_size}")
		else:
			QMessageBox.warning(self, "提示", f"尺寸 {new_size}x{new_size} 已存在！")

	def dragEnterEvent(self, event: QDragEnterEvent):
		"""拖拽进入事件"""
		if event.mimeData().hasUrls():
			event.accept()
			self.drop_label.setStyleSheet("""
                QLabel {
                    border: 2px solid #0078d4;
                    border-radius: 10px;
                    padding: 40px;
                    background-color: #e8f0fe;
                    font-size: 14px;
                }
            """)
		else:
			event.ignore()

	def dragLeaveEvent(self, event):
		"""拖拽离开事件"""
		self.drop_label.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 10px;
                padding: 40px;
                background-color: #f8f9fa;
                font-size: 14px;
            }
            QLabel:hover {
                border-color: #0078d4;
                background-color: #e8f0fe;
            }
        """)

	def dropEvent(self, event: QDropEvent):
		"""拖拽放下事件"""
		files = [u.toLocalFile() for u in event.mimeData().urls()]
		if files:
			self.load_image(files[0])

	def select_image(self):
		"""选择图片文件"""
		file_path, _ = QFileDialog.getOpenFileName(
			self, "选择图片", "",
			"图片文件 (*.png *.jpg *.jpeg *.bmp *.gif);;所有文件 (*.*)"
		)
		if file_path:
			self.load_image(file_path)

	def load_image(self, file_path):
		"""加载图片"""
		# 检查文件是否为图片
		try:
			img = Image.open(file_path)
			self.input_image_path = file_path

			# 显示预览
			pixmap = QPixmap(file_path)
			if pixmap.width() > 300 or pixmap.height() > 300:
				pixmap = pixmap.scaled(300, 300, Qt.AspectRatioMode.KeepAspectRatio,
									   Qt.TransformationMode.SmoothTransformation)

			self.preview_label.setPixmap(pixmap)
			self.preview_label.show()
			self.drop_label.hide()

			# 启用转换按钮
			self.convert_btn.setEnabled(True)
			self.statusBar().showMessage(f"已加载：{os.path.basename(file_path)} (尺寸：{img.width}x{img.height})")

			# 恢复拖放区域样式
			self.dragLeaveEvent(None)

		except Exception as e:
			QMessageBox.critical(self, "错误", f"无法加载图片：{str(e)}")

	def clear_image(self):
		"""清除当前图片"""
		self.input_image_path = None
		self.preview_label.hide()
		self.drop_label.show()
		self.convert_btn.setEnabled(False)
		self.statusBar().showMessage("已清除")

	def convert_to_icon(self):
		"""转换为ICO文件"""
		if not self.input_image_path:
			QMessageBox.warning(self, "警告", "请先选择图片！")
			return

		# 选择保存路径
		default_name = os.path.splitext(os.path.basename(self.input_image_path))[0] + ".ico"
		save_path, _ = QFileDialog.getSaveFileName(
			self, "保存ICO文件", default_name, "ICO文件 (*.ico)"
		)

		if not save_path:
			return

		# 显示进度条
		self.progress_bar.show()
		self.progress_bar.setValue(0)
		self.convert_btn.setEnabled(False)
		self.select_btn.setEnabled(False)

		# 启动转换线程
		self.convert_thread = ConvertThread(self.input_image_path, save_path, self.sizes)
		self.convert_thread.progress.connect(self.update_progress)
		self.convert_thread.finished.connect(self.conversion_finished)
		self.convert_thread.start()

	def update_progress(self, value):
		"""更新进度条"""
		self.progress_bar.setValue(value)

	def conversion_finished(self, success, message):
		"""转换完成"""
		self.progress_bar.hide()
		self.convert_btn.setEnabled(True)
		self.select_btn.setEnabled(True)

		if success:
			QMessageBox.information(self, "成功", message)
			self.statusBar().showMessage("转换完成")
		else:
			QMessageBox.critical(self, "错误", message)
			self.statusBar().showMessage("转换失败")


def main():
	app = QApplication(sys.argv)
	app.setStyle('Fusion')  # 使用Fusion风格，更现代

	window = ImageToIconTool()
	window.show()

	sys.exit(app.exec())


if __name__ == '__main__':
	main()