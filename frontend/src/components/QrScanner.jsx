import { useEffect, useRef, useState } from "react";
import { Html5Qrcode } from "html5-qrcode";
import { useApp } from "../i18n.jsx";

const REGION = "qr-camera-region";
const FILE_REGION = "qr-file-region";

export default function QrScanner({ onResult }) {
  const { t } = useApp();
  const scannerRef = useRef(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");

  async function stop() {
    const scanner = scannerRef.current;
    scannerRef.current = null;
    if (scanner) {
      try {
        if (scanner.isScanning) await scanner.stop();
        scanner.clear();
      } catch {
        /* already stopped */
      }
    }
    setRunning(false);
  }

  async function start() {
    setError("");
    try {
      const scanner = new Html5Qrcode(REGION);
      scannerRef.current = scanner;
      await scanner.start(
        { facingMode: "environment" },
        { fps: 10, qrbox: { width: 240, height: 240 } },
        (text) => {
          stop().then(() => onResult(text));
        },
        () => {}
      );
      setRunning(true);
    } catch {
      scannerRef.current = null;
      setError(t("scan.camErr"));
    }
  }

  async function onFile(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setError("");
    try {
      const scanner = new Html5Qrcode(FILE_REGION);
      const text = await scanner.scanFile(file, false);
      scanner.clear();
      onResult(text);
    } catch {
      setError(t("scan.fileErr"));
    }
  }

  useEffect(() => {
    return () => {
      stop();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="scanner">
      <div id={REGION} className={`scanner-view ${running ? "on" : ""}`} />
      <div id={FILE_REGION} style={{ display: "none" }} />
      {!running ? (
        <div className="row">
          <button type="button" className="btn btn-primary" onClick={start}>
            {t("scan.start")}
          </button>
          <label className="btn btn-ghost">
            {t("scan.upload")}
            <input type="file" accept="image/*" onChange={onFile} hidden />
          </label>
        </div>
      ) : (
        <button type="button" className="btn btn-ghost" onClick={stop}>
          {t("scan.stop")}
        </button>
      )}
      {error && <div className="alert alert-amber">{error}</div>}
    </div>
  );
}
