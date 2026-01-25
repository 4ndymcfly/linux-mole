# Tests de LinuxMole

Suite de tests unitarios para LinuxMole usando pytest.

## 🏗️ Estructura

```
tests/
├── __init__.py           # Marcador de paquete Python
├── conftest.py           # Fixtures compartidas (mocks, temp dirs)
├── test_helpers.py       # Tests para funciones helper (human_bytes, confirm, etc.)
├── test_logging.py       # Tests para sistema de logging
├── test_output.py        # Tests para funciones de output y formateo
└── test_cli.py           # Tests para CLI y argparse
```

## 🚀 Ejecución

### Instalar dependencias

```bash
# Crear entorno virtual
python3 -m venv .venv
source .venv/bin/activate

# Instalar linuxmole con dependencias de desarrollo
pip install -e ".[dev]"
```

### Ejecutar tests

```bash
# Activar entorno virtual
source .venv/bin/activate

# Todos los tests con cobertura (configuración por defecto)
pytest

# Tests sin cobertura
pytest --no-cov

# Tests específicos
pytest tests/test_helpers.py
pytest tests/test_logging.py::TestLogging::test_logger_exists

# Tests con más detalle
pytest -v

# Ver cobertura en HTML
pytest --cov-report=html
open htmlcov/index.html
```

## 📊 Cobertura

**Cobertura actual:** 30.16%
**Mínimo requerido:** 15% ✅
**Nota:** La cobertura mejoró significativamente con los tests de TUI, auto-instalación y comandos.

### Objetivos de cobertura por fase:

- ✅ **Fase 1 (actual):** 15%+ - Tests de infraestructura básica
- 🎯 **Fase 4 (post-modularización):** 40%+ - Tests de módulos individuales
- 🎯 **Final:** 70%+ - Tests completos de todos los comandos

## 🧪 Tests Implementados (120 tests)

### `test_helpers.py` (26 tests)
- `human_bytes()`: Formateo de tamaños (bytes, KB, MB, GB, TB)
- `format_size()`: Formateo con flags opcionales
- `is_root()`: Detección de usuario root
- `confirm()`: Confirmaciones de usuario
- `which()`: Búsqueda de comandos
- `run()`: Ejecución de comandos (dry-run y normal)
- `capture()`: Captura de output de comandos

### `test_logging.py` (8 tests)
- Logger global existe y configuración correcta
- `setup_logging()`: Niveles INFO/DEBUG
- Logging a archivo
- Integración con funciones `run()` y `capture()`

### `test_output.py` (12 tests)
- Funciones de print (`p()`)
- Constantes (VERSION, BANNER, PROJECT_URL)
- Paths de configuración
- Whitelist: carga, parseo y matching de patrones

### `test_cli.py` (6 tests)
- Flags --version y --help
- Modo interactivo (sin argumentos)
- Validación de flags --verbose y --log-file

### `test_uninstall.py` (15 tests) ⭐ FASE 2
- Detección de paquetes APT/Snap/Flatpak
- Paths de configuración de aplicaciones
- Comando `lm uninstall` con todas sus opciones
- Integración con whitelist
- Casos edge: paquete no encontrado, cancelación, whitelisted

### `test_optimize.py` (12 tests) ⭐ FASE 2
- Optimización de databases (locate, man, ldconfig, fonts, MIME)
- Optimización de red (DNS, NetworkManager, ARP)
- Optimización de servicios (systemd)
- Clear cache (página de memoria - PELIGROSO)
- Flags: --all, --database, --network, --services, --clear-cache
- Dry-run y confirmaciones
- Casos edge: sin acciones, cancelación, permisos root

### `test_whitelist.py` (11 tests) ⭐ FASE 3
- Mostrar whitelist vacía y con patrones
- Añadir patrones nuevos y duplicados
- Eliminar patrones existentes y no existentes
- Probar si path está protegido
- Editar whitelist con/sin $EDITOR
- Preservar comentarios al editar
- Strip whitespace en patrones

### `test_tui.py` (16 tests) ⭐ FASE 3
- Análisis sin TUI (modo tabla tradicional)
- TUI no disponible - usuario rechaza instalación
- TUI no disponible - usuario acepta instalación (éxito)
- TUI no disponible - usuario acepta instalación (fallo)
- TUI no disponible - instalación con timeout
- TUI disponible (lanzamiento de app)
- Ordenamiento por tamaño
- Respeto del límite --top
- Manejo de directorio vacío
- Comando du no encontrado
- Expansión de ~ en paths
- Inicialización de DiskAnalyzerApp
- Bindings de teclado (q, r, d)
- Título de la aplicación
- Widget DiskUsageInfo (vacío y con datos)

### `test_config.py` (20 tests) ⭐ FASE 3
- Path del archivo de configuración
- Estructura de configuración por defecto
- Configuración de whitelist por defecto
- Configuración de clean por defecto
- Configuración de paths por defecto
- Configuración de optimize por defecto
- Configuración de TUI por defecto
- Cargar config cuando archivo no existe
- Cargar config sin tomllib disponible
- Cargar config desde archivo válido
- Cargar config desde archivo inválido
- Guardar config crea directorio
- Guardar config escribe archivo TOML
- Guardar config maneja errores
- Comando config sin archivo
- Comando config --reset
- Comando config --reset cancelado
- Comando config --edit sin $EDITOR
- Comando config --edit con $EDITOR
- Comando config muestra configuración

## 🔧 Fixtures Disponibles

Definidas en `conftest.py`:

- `mock_console`: Mock del console de rich
- `temp_config_dir`: Directorio temporal de configuración
- `mock_subprocess`: Mocks de subprocess.run y subprocess.check_output
- `mock_root_user` / `mock_non_root_user`: Simular permisos de usuario
- `capture_output`: Capturar stdout/stderr

## 📝 Convenciones

### Estructura de test
```python
class TestFeatureName:
    """Tests for feature description."""

    def test_specific_behavior(self, fixture_if_needed):
        """Test description."""
        # Arrange
        # Act
        result = function_to_test()
        # Assert
        assert result == expected_value
```

### Naming
- Archivos: `test_*.py`
- Clases: `Test*`
- Funciones: `test_*`

## 🐛 Debugging

### Ver output durante tests
```bash
pytest -s  # No captura stdout/stderr
```

### Ejecutar test específico con debug
```bash
pytest tests/test_helpers.py::TestHumanBytes::test_bytes -v -s
```

### Ver logs de pytest
```bash
pytest --log-cli-level=DEBUG
```

## 📚 Recursos

- [pytest documentation](https://docs.pytest.org/)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
- [pytest-mock documentation](https://pytest-mock.readthedocs.io/)

## 🔄 CI/CD

Los tests se ejecutarán automáticamente en GitHub Actions cuando se implemente CI/CD (Tarea #5).

## ✅ Checklist para agregar tests nuevos

1. [ ] Crear archivo `test_*.py` en `tests/`
2. [ ] Importar módulo a testear
3. [ ] Crear clase `Test*` con docstring
4. [ ] Escribir funciones `test_*` con docstrings
5. [ ] Usar fixtures de `conftest.py` si es necesario
6. [ ] Ejecutar tests: `pytest`
7. [ ] Verificar cobertura: `pytest --cov-report=term-missing`
8. [ ] Actualizar este README si es necesario

---

**Última actualización:** 2026-01-25
**Fase 1 completada:** Sistema de logging (#3) + Tests unitarios (#4)
**Fase 2 completada:** `lm uninstall` (#2) + `lm optimize` (#1)
**Fase 3 parcial:** Whitelist UI (#6) + TUI para analyze (#9)
