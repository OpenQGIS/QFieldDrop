# -*- coding: utf-8 -*-
"""
QField LAN Drop - QGIS Plugin Main Entry Logic
Mounts split dual actions onto QGIS toolbar and plugins menu:
1. [📤 投送至 QField (Drop Out)]: Auto-package & instant distribution dialog
2. [📥 接收 QField 成果 (Drop In)]: Instant receiving mode dialog without packaging overhead
3. [📱 安装手机助手 (Mobile Setup)]: Mobile companion QML installer dialog
"""

import os
from qgis.PyQt.QtWidgets import QAction, QToolBar
from qgis.PyQt.QtGui import QIcon
from qgis.gui import QgisInterface
from qgis.core import Qgis

from .ui.send_dialog import QFieldSendDialog
from .ui.receive_dialog import QFieldReceiveDialog
from .i18n_helper import tr, load_translator, unload_translator


class QFieldDropPlugin:
    def __init__(self, iface: QgisInterface):
        self.iface = iface
        self.action_send = None
        self.action_receive = None
        self.action_mobile = None
        self.dlg_send = None
        self.dlg_receive = None
        self.mobile_dlg = None
        self._standalone_server = None
        self.plugin_dir = os.path.dirname(os.path.abspath(__file__))
        self.translator = load_translator(self.plugin_dir)

    def _clean_stale_actions(self):
        """Purges any lingering ghost/stale actions from toolbars and menus."""
        keywords = ("LAN Drop", "Drop Out", "Drop In", "QField 局域网直传", "投送工程至 QField", "接收 QField 成果", "手机助手")
        obj_names = ("qfielddrop_action_send", "qfielddrop_action_receive", "qfielddrop_action_mobile")

        # 1. Clean from all toolbars
        try:
            main_win = self.iface.mainWindow()
            toolbars = main_win.findChildren(QToolBar) if main_win else []
            for tb in toolbars:
                raw_acts = getattr(tb, 'actions', None)
                acts = raw_acts() if callable(raw_acts) else (raw_acts or [])
                for act in list(acts):
                    t = act.text() or ""
                    obj = act.objectName() or ""
                    if obj in obj_names or any(kw in t for kw in keywords):
                        try:
                            tb.removeAction(act)
                        except (AttributeError, RuntimeError):
                            pass
        except (AttributeError, RuntimeError):
            pass

        # 2. Clean from plugin menu
        try:
            p_menu = self.iface.pluginMenu()
            if p_menu:
                for act in list(p_menu.actions()):
                    if "QField LAN Drop" in (act.text() or ""):
                        if act.menu():
                            for sub_act in list(act.menu().actions()):
                                try:
                                    act.menu().removeAction(sub_act)
                                except (AttributeError, RuntimeError):
                                    pass
                        try:
                            p_menu.removeAction(act)
                        except (AttributeError, RuntimeError):
                            pass
        except (AttributeError, RuntimeError):
            pass

    def initGui(self):
        """Mounts split actions onto QGIS toolbar and menu."""
        # Clean up any stale/ghost actions first (e.g. from hot-reloads)
        self._clean_stale_actions()

        # 优先读取 icons/ 目录（支持用户升级与 Inkscape 批量导出），其次降级回退到 icon/ 与根目录
        icons_dir = os.path.join(self.plugin_dir, "icons")
        icon_dir = os.path.join(self.plugin_dir, "icon")

        def _resolve_icon(name):
            p_icons = os.path.join(icons_dir, name)
            if os.path.exists(p_icons):
                return p_icons
            p_icon = os.path.join(icon_dir, name)
            if os.path.exists(p_icon):
                return p_icon
            return os.path.join(self.plugin_dir, name)

        icon_send_path = _resolve_icon("icon_send.svg")
        icon_receive_path = _resolve_icon("icon_receive.svg")
        icon_mobile_path = _resolve_icon("icon_mobile.svg")

        # Action 1: Outbound Dispatch
        self.action_send = QAction(
            QIcon(icon_send_path),
            tr("Drop Out (Send to QField)"),
            self.iface.mainWindow()
        )
        self.action_send.setObjectName("qfielddrop_action_send")
        self.action_send.setStatusTip(tr("Save, package and transfer current project to QField via QR/LocalSend/ADB"))
        self.action_send.triggered.connect(self.run_send)

        # Action 2: Inbound Return
        self.action_receive = QAction(
            QIcon(icon_receive_path),
            tr("Drop In (Receive from QField)"),
            self.iface.mainWindow()
        )
        self.action_receive.setObjectName("qfielddrop_action_receive")
        self.action_receive.setStatusTip(tr("Start receiving service and retrieve field updates via Web/ADB"))
        self.action_receive.triggered.connect(self.run_receive)

        # Action 3: Mobile Companion Installer
        self.action_mobile = QAction(
            QIcon(icon_mobile_path),
            tr("Install QField Mobile Companion"),
            self.iface.mainWindow()
        )
        self.action_mobile.setObjectName("qfielddrop_action_mobile")
        self.action_mobile.setStatusTip(tr("Install companion QML plugin onto mobile QField"))
        self.action_mobile.triggered.connect(self.run_mobile_install)

        # Add all to Toolbar
        self.iface.addToolBarIcon(self.action_send)
        self.iface.addToolBarIcon(self.action_receive)
        self.iface.addToolBarIcon(self.action_mobile)

        # Add to Menu
        self.iface.addPluginToMenu("&QField LAN Drop", self.action_send)
        self.iface.addPluginToMenu("&QField LAN Drop", self.action_receive)
        self.iface.addPluginToMenu("&QField LAN Drop", self.action_mobile)

    def unload(self):
        """Cleans up toolbar icons and menu items when plugin is disabled/unloaded."""
        if self.dlg_send:
            try:
                self.dlg_send.close()
            except (AttributeError, RuntimeError):
                pass
            self.dlg_send = None

        if self.dlg_receive:
            try:
                self.dlg_receive.close()
            except (AttributeError, RuntimeError):
                pass
            self.dlg_receive = None

        if self.mobile_dlg:
            try:
                self.mobile_dlg.close()
            except (AttributeError, RuntimeError):
                pass
            self.mobile_dlg = None

        if self._standalone_server:
            try:
                self._standalone_server.stop()
            except (AttributeError, RuntimeError, OSError):
                pass
            self._standalone_server = None

        for act in (self.action_send, self.action_receive, self.action_mobile):
            if act:
                try:
                    self.iface.removePluginMenu("&QField LAN Drop", act)
                    self.iface.removeToolBarIcon(act)
                except (AttributeError, RuntimeError):
                    pass
        self.action_send = None
        self.action_receive = None
        self.action_mobile = None

        # Unload QTranslator
        if self.translator:
            self.translator = unload_translator(self.translator)

        # Ensure complete sweep of any residual actions
        self._clean_stale_actions()

    def run_send(self):
        """Triggered by [投送工程至 QField] button (Outbound Dispatch Dialog)."""
        try:
            if getattr(self, '_standalone_server', None):
                try:
                    self._standalone_server.stop()
                except Exception:
                    pass
                self._standalone_server = None

            if self._is_send_dialog_active():
                self.dlg_send.raise_()
                self.dlg_send.activateWindow()
                return

            self.dlg_send = QFieldSendDialog(self.iface.mainWindow(), initial_tab=0)
            if not getattr(self.dlg_send, 'is_ready', False):
                self.dlg_send = None
                return
            self.dlg_send.show()
            self.dlg_send.raise_()
            self.dlg_send.activateWindow()
        except Exception as e:
            self.iface.messageBar().pushMessage(
                "QField LAN Drop", f"打开投送对话框失败: {str(e)}", level=Qgis.Warning, duration=5
            )

    def run_receive(self):
        """Triggered by [接收 QField 成果] button (Inbound Return Dialog, Zero-overhead)."""
        try:
            if self._is_receive_dialog_active():
                self.dlg_receive.raise_()
                self.dlg_receive.activateWindow()
                return

            self.dlg_receive = QFieldReceiveDialog(self.iface.mainWindow())
            self.dlg_receive.show()
            self.dlg_receive.raise_()
            self.dlg_receive.activateWindow()
        except Exception as e:
            self.iface.messageBar().pushMessage(
                "QField LAN Drop", f"打开成果接收对话框失败: {str(e)}", level=Qgis.Warning, duration=5
            )

    def run_mobile_install(self):
        """Triggered by [安装 QField 手机助手] button."""
        from .ui.mobile_install_dialog import MobileInstallDialog
        from .core.net_server import LanDropServer

        try:
            port = 8899
            if self._is_send_dialog_active() and getattr(self.dlg_send, 'port', None):
                port = self.dlg_send.port
            elif self._is_receive_dialog_active() and getattr(self.dlg_receive, 'port', None):
                port = self.dlg_receive.port
            else:
                # Ensure local server is running for mobile.zip distribution
                if not getattr(self, '_standalone_server', None) or not self._standalone_server.is_running:
                    import tempfile
                    t_dir = tempfile.mkdtemp(prefix="qfield_mobile_inst_")
                    self._standalone_server = LanDropServer(t_dir, "dummy.zip", start_port=8899)
                    port = self._standalone_server.start()
                else:
                    port = self._standalone_server.port

            self.mobile_dlg = MobileInstallDialog(port, self.iface.mainWindow())
            def _cleanup_standalone():
                if getattr(self, '_standalone_server', None):
                    try:
                        self._standalone_server.stop()
                    except Exception:
                        pass
                    self._standalone_server = None

            self.mobile_dlg.finished.connect(_cleanup_standalone)
            self.mobile_dlg.show()
            self.mobile_dlg.raise_()
            self.mobile_dlg.activateWindow()
        except Exception as e:
            self.iface.messageBar().pushMessage(
                "QField LAN Drop", f"打开助手安装对话框失败: {str(e)}", level=Qgis.Warning, duration=5
            )

    def _is_send_dialog_active(self) -> bool:
        if self.dlg_send:
            try:
                return self.dlg_send.isVisible()
            except RuntimeError:
                self.dlg_send = None
        return False

    def _is_receive_dialog_active(self) -> bool:
        if self.dlg_receive:
            try:
                return self.dlg_receive.isVisible()
            except RuntimeError:
                self.dlg_receive = None
        return False
