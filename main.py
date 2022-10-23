from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import (
    Qt, QObject, pyqtSignal, QRunnable, pyqtSlot, QThreadPool, QCoreApplication
)
from datetime import datetime
import requests

# APP_GET_LAST_UPDATE: str = "https://ekxb35fje-private-web-api.herokuapp.com/app/last_update"
# APP_DOWNLOAD_URL: str = "https://ekxb35fje-private-web-api.herokuapp.com/app/download"

APP_GET_LAST_UPDATE: str = "http://127.0.0.1:8000/app/last_update"
APP_DOWNLOAD_URL: str = "http://127.0.0.1:8000/app/download"

DATE_FORMAT: str = "%Y-%m-%dT%H:%M:%S.%f"

EXCLUDE_PATHS = [
    '__MACOSX/',
]


def get_current_downloaded_update_date() -> datetime:
    pass


def save_current_downloaded_update_date(date: datetime) -> None:
    pass


def get_last_update() -> datetime:
    date = requests.get(APP_GET_LAST_UPDATE).json()["last_update"]
    return datetime.strptime(date, DATE_FORMAT)


class WorkerSignals(QObject):
    progress = pyqtSignal(int)
    extracting_start = pyqtSignal()
    updating_done = pyqtSignal()
    error = pyqtSignal()


class JobRunner(QRunnable):
    signals = WorkerSignals()

    def __init__(self):
        super().__init__()

    def download_app_zip(self):
        file_name = "app.zip"
        with open(file_name, "wb") as file:
            response = requests.get(APP_DOWNLOAD_URL, stream=True)

            total_length = response.headers.get('content-length')

            if total_length is None:
                file.write(response.content)
            else:
                dl = 0
                total_length = int(total_length)
                for data in response.iter_content(chunk_size=4096):
                    dl += len(data)
                    file.write(data)
                    done = int(100 * dl / total_length)
                    self.signals.progress.emit(done)

    def unzip_app(self):
        import zipfile
        import shutil
        import os

        self.signals.extracting_start.emit()

        if os.path.isdir("app"):
            shutil.rmtree("app")

        with zipfile.ZipFile("app.zip", "r") as zip_file:
            try:
                items = zip_file.infolist()
                total_n = len(items)

                for n, item in enumerate(items, 1):
                    if not any(item.filename.startswith(p) for p in EXCLUDE_PATHS):
                        zip_file.extract(item)

                    self.signals.progress.emit(int(n * 100. / total_n))

            except Exception as e:
                e.with_traceback()
                return

        os.remove("app.zip")

    @pyqtSlot()
    def run(self):
        try:
            # self.download_app_zip()
            # self.unzip_app()
            self.signals.updating_done.emit()
        except Exception as e:
            self.signals.error.emit()
            return


class UpdaterWindow(QWidget):
    switch_window = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.setWindowTitle("MirumApp")

        self.label = QtWidgets.QLabel(text="Downloading", parent=self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.adjustSize()

        self.progress_bar = QtWidgets.QProgressBar(parent=self)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximumHeight(10)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.label, 0)
        layout.addWidget(self.progress_bar, 2)
        layout.setContentsMargins(20, 10, 20, 10)

        self.setFixedSize(300, 50)
        self.setLayout(layout)

        self.threadpool = QThreadPool()

        self.runner = JobRunner()
        self.runner.signals.progress.connect(self.update_progress)
        self.runner.signals.extracting_start.connect(self.change_label_to_extracting)
        self.runner.signals.updating_done.connect(self.updating_done)
        self.runner.signals.error.connect(self.show_error)
        self.threadpool.start(self.runner)

    def change_label_to_extracting(self):
        self.label.setText("Extracting")
        self.label.adjustSize()

    def update_progress(self, n: int):
        self.progress_bar.setValue(n)

    def updating_done(self):
        self.switch_window.emit()

    def show_error(self):
        result = QtWidgets.QMessageBox.critical(self,
                                                "Error", "Something went wrong!",
                                                QtWidgets.QMessageBox.StandardButton.Close)
        QApplication.exit()


class Controller:
    def __init__(self):
        self.main_controller = None
        self.updater = None

    def show_updater(self):
        self.updater = UpdaterWindow()
        self.updater.switch_window.connect(self.show_main)
        self.updater.show()

    def show_main(self):
        if self.updater:
            from app.main import Controller

            self.main_controller = Controller()
            self.updater.close()
            self.main_controller.start()


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    controller = Controller()
    controller.show_updater()
    sys.exit(app.exec())
