import QtQuick 2.14
import QtQuick.Controls 2.14
import QtQuick.Layouts 1.14

Item {
    id: root

    // QField Application Plugin Entry
    function initPlugin(iface) {
        // Register action into QField interface if available
    }

    Dialog {
        id: pullDialog
        title: "QField 局域网极速拉取"
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel

        ColumnLayout {
            spacing: 12
            width: parent.width

            Label {
                text: "请输入电脑端显示的 HTTP 投送地址:"
                font.bold: true
            }

            TextField {
                id: urlField
                Layout.fillWidth: true
                placeholderText: "http://192.168.43.100:8899/project.zip"
                selectByMouse: true
            }

            Label {
                text: "提示: 请确保手机与电脑已连接到同一 Wi-Fi 或手机热点。"
                color: "#666"
                wrapMode: Text.Wrap
                Layout.fillWidth: true
            }
        }

        onAccepted: {
            if (urlField.text.trim().length > 0) {
                Qt.openUrlExternally("qfield://local?import=" + encodeURIComponent(urlField.text.trim()));
            }
        }
    }
}
