"""Pruebas de la lógica compartida por la aplicación y el dashboard."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import numpy as np

from nucleo import guardado
from nucleo.analisis_imagen import analizar
from nucleo.detecciones import PARES_AUTOSOMICOS, resumen_deteccion
from nucleo.db import leer_tabla


def detalle(clase, confianza=0.9):
    return {
        "caja": (0, 0, 10, 10),
        "clase_modelo": clase,
        "clase_final": clase,
        "confianza": confianza,
        "descartada": False,
        "n": 1,
    }


def cariotipo_normal():
    detecciones = []
    for par in PARES_AUTOSOMICOS:
        detecciones.extend([detalle(par), detalle(par)])
    detecciones.extend([detalle("X"), detalle("Y")])
    return detecciones


class DetectorFalso:
    def detectar(self, imagen, conf=None, iou=None):
        return [{"caja": (1, 2, 11, 12), "clase": "A1", "confianza": 0.9}]


class ResumenDeteccionTest(unittest.TestCase):
    def test_cuenta_pares_y_detecciones_dudosas(self):
        detecciones = []
        for par in PARES_AUTOSOMICOS:
            if par == "B4":
                detecciones.append(detalle("B4", confianza=0.3))
            else:
                detecciones.extend([detalle(par), detalle(par)])
        detecciones.extend([detalle("X"), detalle("Y")])

        resumen = resumen_deteccion(detecciones)

        self.assertEqual(resumen["conteo"]["A1"], 2)
        self.assertEqual(resumen["n_baja"], 1)
        self.assertEqual(resumen["pares"], 1)
        self.assertTrue(any("Total" in motivo for motivo in resumen["motivos"]))
        self.assertTrue(any("confianza" in motivo for motivo in resumen["motivos"]))

    def test_cariotipo_normal_no_tiene_motivos(self):
        detecciones = cariotipo_normal()

        resumen = resumen_deteccion(detecciones)

        self.assertEqual(len(detecciones), 46)
        self.assertEqual(resumen["pares"], 0)
        self.assertEqual(resumen["n_baja"], 0)
        self.assertEqual(resumen["motivos"], [])


class AnalizarTest(unittest.TestCase):
    def test_devuelve_detecciones_canonicas_y_resumen(self):
        imagen = np.zeros((50, 60, 3), dtype=np.uint8)

        resultado = analizar(imagen, DetectorFalso())

        deteccion = resultado["detecciones"][0]
        self.assertEqual(deteccion["clase_modelo"], "A1")
        self.assertEqual(deteccion["clase_final"], "A1")
        self.assertEqual(deteccion["n"], 1)
        self.assertEqual(deteccion["caja"], (1, 2, 11, 12))
        self.assertEqual(resultado["imagen_anotada"].shape, imagen.shape)
        self.assertEqual(resultado["conteo"]["A1"], 1)
        self.assertIn("motivos", resultado)


class GuardadoTest(unittest.TestCase):
    def setUp(self):
        self.original = guardado.guardar_analisis
        self.capturado = {}

        def guardar_falso(nombre_imagen, detecciones, ancho=None, alto=None,
                          ruta_imagen=None, observaciones=None,
                          imagen_resultado=None, resultado=None):
            self.capturado.update({
                "nombre_imagen": nombre_imagen,
                "detecciones": detecciones,
                "ancho": ancho,
                "alto": alto,
                "ruta_imagen": ruta_imagen,
                "observaciones": observaciones,
                "imagen_resultado": imagen_resultado,
                "resultado": resultado,
            })
            return 99

        guardado.guardar_analisis = guardar_falso

    def tearDown(self):
        guardado.guardar_analisis = self.original

    def test_mezcla_activas_y_descartadas(self):
        imagen = np.zeros((40, 30, 3), dtype=np.uint8)

        id_estudio, rutas = guardado.guardar_resultado(
            "foto.jpg", [detalle("A1")], [detalle("B4")], imagen=imagen,
        )

        self.assertEqual(id_estudio, 99)
        self.assertEqual(self.capturado["ancho"], 30)
        self.assertEqual(self.capturado["alto"], 40)
        self.assertEqual(len(self.capturado["detecciones"]), 2)

        activa, descartada = self.capturado["detecciones"]
        self.assertFalse(activa["descartada"])
        self.assertIsNone(descartada["clase_final"])
        self.assertTrue(descartada["descartada"])
        self.assertIsNone(self.capturado["resultado"])
        self.assertEqual(rutas, {"original": None, "resultado": None})

    def test_revisado_genera_resultado(self):
        imagen = np.zeros((10, 10, 3), dtype=np.uint8)

        guardado.guardar_resultado(
            "foto.jpg", cariotipo_normal(), imagen=imagen, revisado=True,
        )

        resultado = self.capturado["resultado"]
        self.assertIsNotNone(resultado)
        self.assertEqual(resultado["cariotipo"], "46,XY")
        self.assertEqual(resultado["alteracion"], "Sin alteraciones numéricas detectadas")

    def test_guarda_archivos_en_carpeta_configurada(self):
        imagen = np.zeros((10, 10, 3), dtype=np.uint8)
        anotada = np.zeros((10, 10, 3), dtype=np.uint8)

        with tempfile.TemporaryDirectory() as temporal:
            carpeta = Path(temporal)
            with patch.object(guardado, "CARPETA_IMAGENES", carpeta):
                _, rutas = guardado.guardar_resultado(
                    "foto.jpg", [detalle("A1")], imagen=imagen,
                    imagen_anotada=anotada, bytes_imagen=b"contenido",
                    guardar_archivos=True,
                )

            self.assertTrue(rutas["original"].exists())
            self.assertTrue(rutas["resultado"].exists())
            self.assertEqual(rutas["original"].read_bytes(), b"contenido")

        self.assertEqual(self.capturado["ruta_imagen"], str(rutas["original"]))
        self.assertEqual(self.capturado["imagen_resultado"], str(rutas["resultado"]))


class LeerTablaTest(unittest.TestCase):
    def test_rechaza_nombres_fuera_de_la_lista_blanca(self):
        with self.assertRaises(ValueError):
            leer_tabla("estudios; DROP TABLE estudios")


if __name__ == "__main__":
    unittest.main()
