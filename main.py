import sys
import sqlite3
import os
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QModelIndex
from PyQt5.QtWidgets import (QMainWindow, QApplication, QTreeView, QTableWidget,
                             QDockWidget, QSplitter, QAction, QTabWidget, QToolBar,
                             QFileDialog, QTableWidgetItem, QVBoxLayout, QWidget,
                             QProgressBar, QLabel, QStatusBar)
from PyQt5.QtGui import QIcon, QStandardItemModel, QStandardItem

class DatabaseLoader(QThread):
    progress = pyqtSignal(int)  # Signal to update the progress bar
    finished = pyqtSignal(list)  # Signal when loading is finished (sends tables)

    def __init__(self, db_path):
        super().__init__()
        self.db_path = db_path

    def run(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Fetch the list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        table_list = []
        total_tables = len(tables)

        # Load tables and emit progress
        for idx, table in enumerate(tables):
            table_list.append(table[0])
            progress_value = int(((idx + 1) / total_tables) * 100)
            self.progress.emit(progress_value)

        conn.close()
        self.finished.emit(table_list)  # Emit the finished signal with table list

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('SQLite Database Viewer')
        self.resize(1200, 800)

        # Initialize the UI
        self.initUI()

        # Hold references to multiple databases and their parent nodes
        self.database_items = {}

         # Explicitly set the menu bar
        self.setMenuBar(self.menuBar())

    def initUI(self):
        # Create Menus
        self.createMenus()

        # Create Toolbar
        self.createToolbar()

        # Create Dock and Splitter for Tree View and Tabs
        self.createDockAndSplitter()

        # Create Status Bar and Progress Bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.progressBar = QProgressBar()
        self.statusLabel = QLabel("Ready")
        self.statusBar.addPermanentWidget(self.statusLabel)
        self.statusBar.addPermanentWidget(self.progressBar)
        self.progressBar.setVisible(False)

         # Ensure the menu bar is in focus
        self.menuBar().setFocus()

    def createMenus(self):
        # File Menu
        fileMenu = self.menuBar().addMenu('File')
        newSessionAction = QAction('New Session', self)
        newSessionAction.triggered.connect(self.newSession)
        importAction = QAction('Import', self)
        exitAction = QAction('Exit', self)
        exitAction.triggered.connect(self.close)

        fileMenu.addAction(newSessionAction)
        fileMenu.addAction(importAction)
        fileMenu.addSeparator()
        fileMenu.addAction(exitAction)

        # Other menus (Options, Help)
        optionsMenu = self.menuBar().addMenu('Options')
        helpMenu = self.menuBar().addMenu('Help')

    def createToolbar(self):
        toolbar = QToolBar("Toolbar", self)
        self.addToolBar(toolbar)

        # Toolbar actions
        newSessionAction = QAction(QIcon('resources/icons/new.png'), 'New Session', self)
        importAction = QAction(QIcon('resources/icons/import.png'), 'Import', self)
        addAction = QAction(QIcon('resources/icons/add.png'), 'Add', self)
        editAction = QAction(QIcon('resources/icons/edit.png'), 'Edit', self)
        deleteAction = QAction(QIcon('resources/icons/delete.png'), 'Delete', self)
        closeAction = QAction(QIcon('resources/icons/close.png'), 'Close', self)
        closeAllTabsAction = QAction("Close All Tabs", self)
        closeAllTabsAction.triggered.connect(self.closeAllTabs)

        toolbar.addAction(newSessionAction)
        toolbar.addAction(importAction)
        toolbar.addAction(addAction)
        toolbar.addAction(editAction)
        toolbar.addAction(deleteAction)
        toolbar.addAction(closeAction)
        toolbar.addAction(closeAllTabsAction)

    def createDockAndSplitter(self):
        splitter = QSplitter(Qt.Horizontal, self)

        # TreeView for listing tables grouped by database
        self.treeView = QTreeView()
        self.treeView.setHeaderHidden(True)  # Hide headers for cleaner look
        dock = QDockWidget("Tables", self)
        dock.setWidget(self.treeView)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)

         # Set maximum width of the left dock (TreeView)
        dock.setMaximumWidth(300)  # You can change this value as needed

        # Dock widget for the tab containing table data
        self.dataDockWidget = QDockWidget("Table Data", self)
        self.tabWidget = QTabWidget()
        self.tabWidget.setTabsClosable(True)  # Make tabs closable
        self.tabWidget.tabCloseRequested.connect(self.closeTab)  # Connect close event
        self.dataDockWidget.setWidget(self.tabWidget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dataDockWidget)

        # Create a model for TreeView
        self.treeModel = QStandardItemModel()
        self.treeView.setModel(self.treeModel)
        self.treeView.clicked.connect(self.onTreeItemClicked)

    def newSession(self):
        # Open file dialog to select a SQLite database
        db_path, _ = QFileDialog.getOpenFileName(self, 'Open Database', '', 'SQLite Database Files (*.db)')
        if db_path:
            db_name = os.path.basename(db_path)
            self.loadDatabase(db_name, db_path)

    def loadDatabase(self, db_name, db_path):
        # Check if the database is already loaded
        if db_name in self.database_items:
            return

        # Store database file path
        self.database_items[db_name] = {'path': db_path}

        # Start loading the database in a separate thread
        self.progressBar.setVisible(True)
        self.progressBar.setValue(0)
        self.statusLabel.setText(f"Loading {db_name}...")

        self.loaderThread = DatabaseLoader(db_path)
        self.loaderThread.progress.connect(self.updateProgressBar)
        self.loaderThread.finished.connect(lambda tables: self.onDatabaseLoaded(db_name, tables))
        self.loaderThread.start()

    def onDatabaseLoaded(self, db_name, tables):
        """Called when database loading is finished, and tables are ready."""
        self.progressBar.setVisible(False)
        self.statusLabel.setText(f"Loaded {db_name}")

        # Create a parent item for this database
        db_item = QStandardItem(QIcon('resources/icons/database.png'), db_name)
        self.treeModel.appendRow(db_item)

        # Add tables as child items under the database
        for table in tables:
            table_item = QStandardItem(QIcon('resources/icons/table.png'), table)
            db_item.appendRow(table_item)

    def updateProgressBar(self, value):
        """Update the progress bar value."""
        self.progressBar.setValue(value)

    def onTreeItemClicked(self, index: QModelIndex):
        """Handles tree view item clicks and loads the corresponding table."""
        item = self.treeModel.itemFromIndex(index)
        parent = item.parent()

        if parent is not None:
            # If clicked on a table, load table data
            db_name = parent.text()
            table_name = item.text()
            self.dataDockWidget.setWindowTitle(f"Table: {table_name} ({db_name})")
            self.addTableTab(db_name, table_name)
        else:
            # If clicked on a database, just update the dock widget title
            db_name = item.text()
            self.dataDockWidget.setWindowTitle(f"Database: {db_name}")

    def addTableTab(self, db_name, table_name):
        """Loads data from the selected table into a new tab."""
        db_info = self.database_items.get(db_name)
        if not db_info:
            return

        db_path = db_info['path']
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        try:
            # Fetch the table data and column names
            cursor.execute(f'SELECT * FROM {table_name}')
            data = cursor.fetchall()
            cursor.execute(f'PRAGMA table_info({table_name})')  # Get column information
            columns = cursor.fetchall()

            # Create a new QTableWidget
            table_widget = QTableWidget()
            table_widget.setRowCount(len(data))
            table_widget.setColumnCount(len(columns))

            # Set column headers
            column_names = [col[1] for col in columns]
            table_widget.setHorizontalHeaderLabels(column_names)

            # Populate the table with data
            for row, rowData in enumerate(data):
                for col, item in enumerate(rowData):
                    table_widget.setItem(row, col, QTableWidgetItem(str(item)))

            # Add the table to a new tab with an icon
            tab_icon = QIcon('resources/icons/table.png')
            self.tabWidget.addTab(table_widget, tab_icon, table_name)

            # Automatically select the newly added tab
            self.tabWidget.setCurrentIndex(self.tabWidget.count() - 1)

        except sqlite3.Error as e:
            print(f"Error loading table {table_name}: {e}")
        finally:
            conn.close()

    def closeAllTabs(self):
        self.tabWidget.clear()

    def closeTab(self, index):
        """Close the tab at the given index."""
        self.tabWidget.removeTab(index)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
