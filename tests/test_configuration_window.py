"""Tests de configuration_window — regresión de dos crash encontrados por el
usuario al usar la UI (2026-10-26):

1. El botón "Guardar todo" hacia ``command=self._save_all`` EN LA CONSTRUCCIÓN
   de la ventana: si el método no existe, la ventana de configuración ni
   siquiera abre (AttributeError inmediato).
2. ``_ejecutar`` del diálogo de corrida usaba ``site_vars`` (viejo diseño de
   checkboxes) en vez del set ``seleccionados`` del Treeview (NameError al
   ejecutar un barrido). Ese closure no es testeable en aislado; el fix se
   verifica por inspección y uso manual.
"""
import os
import tempfile
import unittest

from jobpulse_v15 import configuration_window
from jobpulse_v15.configuration_window import ConfigurationWindow, _save_env_values


class TestBotonGuardarTodo(unittest.TestCase):
    def test_save_all_existe_y_es_llamable(self) -> None:
        # El botón referencia self._save_all al construirse: sin este método
        # la ConfigurationWindow no abre nunca.
        self.assertTrue(callable(getattr(ConfigurationWindow, "_save_all", None)))


class TestSaveEnvValues(unittest.TestCase):
    """El writer de .env debe actualizar sin perder claves ajenas."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.env_path = os.path.join(self._tmp.name, ".env")
        self._orig = configuration_window.ENV_PATH
        configuration_window.ENV_PATH = self.env_path

    def tearDown(self) -> None:
        configuration_window.ENV_PATH = self._orig
        self._tmp.cleanup()

    def _leer(self) -> str:
        with open(self.env_path, encoding="utf-8") as f:
            return f.read()

    def test_archivo_nuevo_agrega_claves(self) -> None:
        _save_env_values({"IA_PROVEEDOR": "custom", "IA_MODEL": "gemma4"})
        contenido = self._leer()
        self.assertIn("IA_PROVEEDOR=custom", contenido)
        self.assertIn("IA_MODEL=gemma4", contenido)

    def test_actualiza_sin_perder_lineas_ajenas(self) -> None:
        with open(self.env_path, "w", encoding="utf-8") as f:
            f.write("# comentario local\nGEMINI_API_KEY=secreto\nIA_MODEL=viejo\n")
        _save_env_values({"IA_MODEL": "nuevo"})
        contenido = self._leer()
        self.assertIn("# comentario local", contenido)
        self.assertIn("GEMINI_API_KEY=secreto", contenido)
        self.assertIn("IA_MODEL=nuevo", contenido)
        self.assertNotIn("IA_MODEL=viejo", contenido)

    def test_valor_con_saltos_de_linea_se_sanitiza(self) -> None:
        _save_env_values({"IA_API_KEY": "abc\r\ndef"})
        self.assertIn("IA_API_KEY=abc  def", self._leer())


if __name__ == "__main__":
    unittest.main()
