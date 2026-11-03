"""Gráficos de revisión y correcciones."""

import altair as alt

from nucleo.constantes import AZUL

from .tema import eje_entero


def confusiones(tabla):
    """Confusiones más frecuentes del modelo, ordenadas por cantidad."""
    return alt.Chart(tabla).mark_bar(color=AZUL).encode(
        y=alt.Y("Confusión:N", sort="-x", title=None),
        x=alt.X(
            "veces:Q",
            title="Veces",
            axis=eje_entero(0, int(tabla["veces"].max()), "Veces"),
        ),
        tooltip=["Confusión", "veces"],
    ).properties(width="container", height=max(120, 28 * len(tabla) + 40))
