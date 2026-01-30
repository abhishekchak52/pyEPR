"""Reporter wrapper for pyaedt gRPC compatibility."""

import os

from .. import logger


class _ReporterWrapper:
    """Wrapper for ReportSetup COM module; uses PyAEDT native API where gRPC COM fails."""
    def __init__(self, reporter_module, design):
        self._reporter = reporter_module
        self._design = design

    def ExportToFile(self, report_name, filepath):
        filepath = os.path.abspath(str(filepath))
        pyaedt_app = self._design._get_pyaedt_app()
        if pyaedt_app is not None:
            try:
                if hasattr(pyaedt_app, "post") and hasattr(pyaedt_app.post, "export_report_to_file"):
                    output_dir = os.path.dirname(filepath)
                    if not output_dir:
                        output_dir = os.getcwd()
                    _, ext = os.path.splitext(filepath)
                    if not ext:
                        ext = ".csv"
                    pyaedt_app.post.export_report_to_file(
                        output_dir=output_dir,
                        plot_name=report_name,
                        extension=ext,
                    )
                    import shutil
                    expected_file = os.path.join(output_dir, f"{report_name}{ext}")
                    if os.path.exists(expected_file) and os.path.abspath(expected_file) != filepath:
                        shutil.move(expected_file, filepath)
                    logger.debug(f"Exported report {report_name} to {filepath} via PyAEDT")
                    return
            except Exception as e:
                logger.debug(f"PyAEDT export_report_to_file failed: {e}, falling back to COM")
        try:
            self._reporter.ExportToFile(report_name, filepath)
        except Exception as e:
            logger.error(f"ExportToFile failed for report {report_name}: {e}")
            raise

    def __getattr__(self, name):
        return getattr(self._reporter, name)
