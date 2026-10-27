# -*- coding: utf-8 -*-
"""
QField LAN Drop - QGIS Plugin Main Entry Logic
Mounts split dual actions onto QGIS toolbar and plugins menu:
1. [📤 投送至 QField (Drop Out)]: Auto-package & instant distribution
2. [📥 接收 QField 成果 (Drop In)]: Instant receiving mode without packaging overhead
"""

import os
from qgis.PyQt.QtWidgets import QAction, QToolBar
from qgis.PyQt.QtGui import QIcon
from qgis.gui import QgisInterface
from qgis.core import Qgis

from .ui.share_dialog import QFieldLanDropDialog


class QFieldDropPlugin:
    def __init__(self, iface: QgisInterface):
        self.iface = iface
        self.action_send = None
        self.action_receive = None
        self.dlg = None
        self.plugin_dir = os.path.dirname(os.path.abspath(__file__))

    def _clean_stale_actions(self):
        """Purges any lingering ghost/stale actions from toolbars and menus."""
        keywords = ("LAN Drop", "Drop Out", "Drop In", "QField 局域网直传", "投送工程至 QField", "接收 QField 成果")
        obj_names = ("qfielddrop_action_send", "qfielddrop_action_receive")

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
                        except Exception:
                            pass
        except Exception:
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
                                except Exception:
                                    pass
                        try:
                            p_menu.removeAction(act)
                        except Exception:
                            pass
        except Exception:
            pass

    def initGui(self):
        """Mounts split actions onto QGIS toolbar and menu."""
        # Clean up any stale/ghost actions first (e.g. from hot-reloads)
        self._clean_stale_actions()

        # Check icon/ directory first, fallback to root
        icon_send_path = os.path.join(self.plugin_dir, "icon", "icon_send.svg")
        if not os.path.exists(icon_send_path):
            icon_send_path = os.path.join(self.plugin_dir, "icon_send.svg")

        icon_receive_path = os.path.join(self.plugin_dir, "icon", "icon_receive.svg")
        if not os.path.exists(icon_receive_path):
            icon_receive_path = os.path.join(self.plugin_dir, "icon_receive.svg")

        # Action 1: Outbound Dispatch
        self.action_send = QAction(
            QIcon(icon_send_path),
            "📤 投送工程至 QField (Drop Out)",
            self.iface.mainWindow()
        )
        self.action_send.setObjectName("qfielddrop_action_send")
        self.action_send.setStatusTip("一键保存、打包并投送当前工程至外业手机 QField (扫码唤醒 / LocalSend / ADB)")
        self.action_send.triggered.connect(self.run_send)

        # Action 2: Inbound Return
        self.action_receive = QAction(
            QIcon(icon_receive_path),
            "📥 接收 QField 成果 (Drop In)",
            self.iface.mainWindow()
        )
        self.action_receive.setObjectName("qfielddrop_action_receive")
        self.action_receive.setStatusTip("一键开启成果接收服务，从手机回传外业成果 (网页扫码 / ADB拉取，无需重新打包)")
        self.action_receive.triggered.connect(self.run_receive)

        # Add both to Toolbar
        self.iface.addToolBarIcon(self.action_send)
        self.iface.addToolBarIcon(self.action_receive)

        # Add to Menu
        self.iface.addPluginToMenu("&QField LAN Drop", self.action_send)
        self.iface.addPluginToMenu("&QField LAN Drop", self.action_receive)

    def unload(self):
        """Cleans up toolbar icons and menu items when plugin is disabled/unloaded."""
        if self.dlg:
            try:
                self.dlg.close()
            except Exception:
                pass
            self.dlg = None

        if self.action_send:
            try:
                self.iface.removePluginMenu("&QField LAN Drop", self.action_send)
                self.iface.removeToolBarIcon(self.action_send)
            except Exception:
                pass
            self.action_send = None

        if self.action_receive:
            try:
                self.iface.removePluginMenu("&QField LAN Drop", self.action_receive)
                self.iface.removeToolBarIcon(self.action_receive)
            except Exception:
                pass
            self.action_receive = None

        # Ensure complete sweep of any residual actions
        self._clean_stale_actions()

    def run_send(self):
        """Triggered by [📤 投送工程至 QField] button."""
        try:
            if self._is_dialog_active():
                self.dlg.tabs.setCurrentIndex(0)
                self.dlg.raise_()
                self.dlg.activateWindow()
                return

            self.dlg = QFieldLanDropDialog(self.iface.mainWindow(), initial_tab=0, auto_package=True)
            self.dlg.show()
            self.dlg.raise_()
            self.dlg.activateWindow()
        except Exception as e:
            self.iface.messageBar().pushMessage(
                "QField LAN Drop", f"打开投送对话框失败: {str(e)}", level=Qgis.Warning, duration=5
            )

    def run_receive(self):
        """Triggered by [📥 接收 QField 成果] button (Zero-overhead, instant open)."""
        try:
            if self._is_dialog_active():
                self.dlg.tabs.setCurrentIndex(2)
                self.dlg.raise_()
                self.dlg.activateWindow()
                return

            self.dlg = QFieldLanDropDialog(self.iface.mainWindow(), initial_tab=2, auto_package=False)
            self.dlg.show()
            self.dlg.raise_()
            self.dlg.activateWindow()
        except Exception as e:
            self.iface.messageBar().pushMessage(
                "QField LAN Drop", f"打开接收对话框失败: {str(e)}", level=Qgis.Warning, duration=5
            )

    def _is_dialog_active(self) -> bool:
        if self.dlg:
            try:
                return self.dlg.isVisible() and hasattr(self.dlg, 'tabs')
            except RuntimeError:
                self.dlg = None
        return False
