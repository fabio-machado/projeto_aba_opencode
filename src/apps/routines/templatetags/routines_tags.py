"""
Template tags customizados para o módulo Routines.
"""

import json

from django import template

register = template.Library()


@register.filter(name="jsonify", is_safe=True)
def jsonify(value):
    """Serializa um objeto Python para JSON seguro (sem escapes de HTML).

    Uso:  {{ my_dict|jsonify|safe }}

    Args:
        value: Qualquer objeto serializável por json.dumps.

    Returns:
        String JSON segura para inclusão em <script>.
    """
    return json.dumps(value, ensure_ascii=False, default=str)


@register.filter(name="jsonify_or_null", is_safe=True)
def jsonify_or_null(value):
    """Serializa objeto para JSON ou retorna 'null' se None/falsy.

    Uso:  {{ my_object|jsonify_or_null|safe }}

    Args:
        value: Objeto Python ou None.

    Returns:
        String JSON ou 'null'.
    """
    if value is None:
        return "null"
    return json.dumps(value, ensure_ascii=False, default=str)
