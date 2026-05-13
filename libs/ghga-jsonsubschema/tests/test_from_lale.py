"""Tests derived from the Lale machine learning pipeline project.

Originally created on August 24, 2019 by Andrew Habib.
Contains changes by The GHGA Authors.
SPDX-License-Identifier: Apache-2.0
"""

from jsonsubschema import isSubschema


def test_1():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_2():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_3():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_4():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_5():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_6():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_7():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_8():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_9():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_10():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_11():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_12():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_13():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_14():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_15():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_16():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_17():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_18():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_19():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_20():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_21():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_22():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_23():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_24():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance", "exponential"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_25():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_26():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_27():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_28():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_29():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_30():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_31():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_32():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_33():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_34():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_35():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_36():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_37():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_38():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_39():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_40():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_41():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_42():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_43():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_44():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_45():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_46():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_47():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_48():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["deviance"]},
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_49():
    s1 = {
        "type": "object",
        "properties": {"boosting_type": {"not": {"enum": ["rf"]}}},
    }
    s2 = {
        "type": "object",
        "properties": {
            "subsample_freq": {"not": {"enum": [0]}},
            "subsample": {"not": {"enum": [1.0]}},
        },
    }

    assert not isSubschema(s1, s2)


def test_50():
    s1 = {
        "type": "object",
        "properties": {
            "subsample_freq": {"not": {"enum": [0]}},
            "subsample": {"not": {"enum": [1.0]}},
        },
    }
    s2 = {
        "type": "object",
        "properties": {"boosting_type": {"not": {"enum": ["rf"]}}},
    }

    assert not isSubschema(s1, s2)


def test_51():
    s1 = {
        "type": "object",
        "properties": {"boosting_type": {"not": {"enum": ["rf", "goss"]}}},
    }
    s2 = {
        "type": "object",
        "properties": {
            "subsample_freq": {"not": {"enum": [0]}},
            "subsample": {"not": {"enum": [1.0]}},
            "boosting_type": {"not": {"enum": ["goss"]}},
        },
    }

    assert not isSubschema(s1, s2)


def test_52():
    s1 = {
        "type": "object",
        "properties": {"boosting_type": {"not": {"enum": ["rf", "goss"]}}},
    }
    s2 = {
        "type": "object",
        "properties": {"subsample_freq": {"not": {}}, "subsample": {"not": {}}},
    }

    assert not isSubschema(s1, s2)


def test_53():
    s1 = {
        "type": "object",
        "properties": {
            "subsample_freq": {"not": {"enum": [0]}},
            "subsample": {"not": {"enum": [1.0]}},
            "boosting_type": {"not": {"enum": ["goss"]}},
        },
    }
    s2 = {
        "type": "object",
        "properties": {"boosting_type": {"not": {"enum": ["rf", "goss"]}}},
    }

    assert not isSubschema(s1, s2)


def test_54():
    s1 = {
        "type": "object",
        "properties": {
            "subsample_freq": {"not": {"enum": [0]}},
            "subsample": {"not": {"enum": [1.0]}},
            "boosting_type": {"not": {"enum": ["goss"]}},
        },
    }
    s2 = {
        "type": "object",
        "properties": {
            "boosting_type": {"not": {"enum": ["rf"]}},
            "subsample_freq": {"enum": [0]},
            "subsample": {"enum": [1.0]},
        },
    }

    assert not isSubschema(s1, s2)


def test_55():
    s1 = {
        "type": "object",
        "properties": {
            "subsample_freq": {"not": {"enum": [0]}},
            "subsample": {"not": {"enum": [1.0]}},
            "boosting_type": {"not": {"enum": ["goss"]}},
        },
    }
    s2 = {
        "type": "object",
        "properties": {"subsample_freq": {"not": {}}, "subsample": {"not": {}}},
    }

    assert not isSubschema(s1, s2)


def test_56():
    s1 = {
        "type": "object",
        "properties": {"subsample_freq": {"not": {}}, "subsample": {"not": {}}},
    }
    s2 = {
        "type": "object",
        "properties": {"boosting_type": {"not": {"enum": ["rf", "goss"]}}},
    }

    assert not isSubschema(s1, s2)


def test_57():
    s1 = {
        "type": "object",
        "properties": {"subsample_freq": {"not": {}}, "subsample": {"not": {}}},
    }
    s2 = {
        "type": "object",
        "properties": {
            "boosting_type": {"not": {"enum": ["rf"]}},
            "subsample_freq": {"enum": [0]},
            "subsample": {"enum": [1.0]},
        },
    }

    assert not isSubschema(s1, s2)


def test_58():
    s1 = {
        "type": "object",
        "properties": {"subsample_freq": {"not": {}}, "subsample": {"not": {}}},
    }
    s2 = {
        "type": "object",
        "properties": {
            "subsample_freq": {"not": {"enum": [0]}},
            "subsample": {"not": {"enum": [1.0]}},
            "boosting_type": {"not": {"enum": ["goss"]}},
        },
    }

    assert not isSubschema(s1, s2)


def test_59():
    s1 = {
        "type": "object",
        "properties": {
            "boosting_type": {"enum": ["gbdt", "dart"]},
            "max_depth": {
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 50,
                "maximumForOptimizer": 500,
            },
            "min_child_samples": {
                "default": 20,
                "type": "integer",
                "minimumForOptimizer": 1,
                "maximumForOptimizer": 20,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimum": 0.0,
                "exclusiveMinimum": True,
                "minimumForOptimizer": 0.1,
                "maximum": 1.0,
            },
            "subsample_freq": {
                "default": 0,
                "type": "integer",
                "minimumForOptimizer": 0,
                "maximumForOptimizer": 10,
            },
        },
        "additionalProperties": False,
        "required": [
            "min_child_samples",
            "max_depth",
            "n_estimators",
            "subsample_freq",
            "boosting_type",
            "subsample",
            "learning_rate",
        ],
    }
    s2 = {
        "type": "object",
        "properties": {
            "boosting_type": {"enum": ["gbdt", "dart", "rf"]},
            "max_depth": {
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 50,
                "maximumForOptimizer": 500,
            },
            "min_child_samples": {
                "default": 20,
                "type": "integer",
                "minimumForOptimizer": 1,
                "maximumForOptimizer": 20,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimum": 0.0,
                "exclusiveMinimum": True,
                "minimumForOptimizer": 0.1,
                "maximum": 1.0,
                "exclusiveMaximum": True,
            },
            "subsample_freq": {
                "allOf": [
                    {
                        "default": 0,
                        "type": "integer",
                        "minimumForOptimizer": 0,
                        "exclusiveMinimumForOptimizer": True,
                        "maximumForOptimizer": 10,
                    },
                    {"not": {"enum": [0]}},
                ]
            },
        },
        "additionalProperties": False,
        "required": [
            "min_child_samples",
            "max_depth",
            "n_estimators",
            "subsample_freq",
            "boosting_type",
            "subsample",
            "learning_rate",
        ],
    }

    assert not isSubschema(s1, s2)


def test_60():
    s1 = {
        "type": "object",
        "properties": {
            "boosting_type": {"enum": ["gbdt", "dart", "rf"]},
            "max_depth": {
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 50,
                "maximumForOptimizer": 500,
            },
            "min_child_samples": {
                "default": 20,
                "type": "integer",
                "minimumForOptimizer": 1,
                "maximumForOptimizer": 20,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimum": 0.0,
                "exclusiveMinimum": True,
                "minimumForOptimizer": 0.1,
                "maximum": 1.0,
                "exclusiveMaximum": True,
            },
            "subsample_freq": {
                "allOf": [
                    {
                        "default": 0,
                        "type": "integer",
                        "minimumForOptimizer": 0,
                        "exclusiveMinimumForOptimizer": True,
                        "maximumForOptimizer": 10,
                    },
                    {"not": {"enum": [0]}},
                ]
            },
        },
        "additionalProperties": False,
        "required": [
            "min_child_samples",
            "max_depth",
            "n_estimators",
            "subsample_freq",
            "boosting_type",
            "subsample",
            "learning_rate",
        ],
    }
    s2 = {
        "type": "object",
        "properties": {
            "boosting_type": {"enum": ["gbdt", "dart"]},
            "max_depth": {
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 50,
                "maximumForOptimizer": 500,
            },
            "min_child_samples": {
                "default": 20,
                "type": "integer",
                "minimumForOptimizer": 1,
                "maximumForOptimizer": 20,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimum": 0.0,
                "exclusiveMinimum": True,
                "minimumForOptimizer": 0.1,
                "maximum": 1.0,
            },
            "subsample_freq": {
                "default": 0,
                "type": "integer",
                "minimumForOptimizer": 0,
                "maximumForOptimizer": 10,
            },
        },
        "additionalProperties": False,
        "required": [
            "min_child_samples",
            "max_depth",
            "n_estimators",
            "subsample_freq",
            "boosting_type",
            "subsample",
            "learning_rate",
        ],
    }

    assert not isSubschema(s1, s2)


def test_61():
    s1 = {
        "type": "object",
        "properties": {"boosting_type": {"not": {"enum": ["rf"]}}},
    }
    s2 = {
        "type": "object",
        "properties": {
            "subsample_freq": {"not": {"enum": [0]}},
            "subsample": {"not": {"enum": [1.0]}},
        },
    }

    assert not isSubschema(s1, s2)


def test_62():
    s1 = {
        "type": "object",
        "properties": {
            "subsample_freq": {"not": {"enum": [0]}},
            "subsample": {"not": {"enum": [1.0]}},
        },
    }
    s2 = {
        "type": "object",
        "properties": {"boosting_type": {"not": {"enum": ["rf"]}}},
    }

    assert not isSubschema(s1, s2)


def test_63():
    s1 = {
        "type": "object",
        "properties": {"boosting_type": {"not": {"enum": ["rf", "goss"]}}},
    }
    s2 = {
        "type": "object",
        "properties": {
            "subsample_freq": {"not": {"enum": [0]}},
            "subsample": {"not": {"enum": [1.0]}},
            "boosting_type": {"not": {"enum": ["goss"]}},
        },
    }

    assert not isSubschema(s1, s2)


def test_64():
    s1 = {
        "type": "object",
        "properties": {"boosting_type": {"not": {"enum": ["rf", "goss"]}}},
    }
    s2 = {
        "type": "object",
        "properties": {"subsample_freq": {"not": {}}, "subsample": {"not": {}}},
    }

    assert not isSubschema(s1, s2)


def test_65():
    s1 = {
        "type": "object",
        "properties": {
            "subsample_freq": {"not": {"enum": [0]}},
            "subsample": {"not": {"enum": [1.0]}},
            "boosting_type": {"not": {"enum": ["goss"]}},
        },
    }
    s2 = {
        "type": "object",
        "properties": {"boosting_type": {"not": {"enum": ["rf", "goss"]}}},
    }

    assert not isSubschema(s1, s2)


def test_66():
    s1 = {
        "type": "object",
        "properties": {
            "subsample_freq": {"not": {"enum": [0]}},
            "subsample": {"not": {"enum": [1.0]}},
            "boosting_type": {"not": {"enum": ["goss"]}},
        },
    }
    s2 = {
        "type": "object",
        "properties": {
            "boosting_type": {"not": {"enum": ["rf"]}},
            "subsample_freq": {"enum": [0]},
            "subsample": {"enum": [1.0]},
        },
    }

    assert not isSubschema(s1, s2)


def test_67():
    s1 = {
        "type": "object",
        "properties": {
            "subsample_freq": {"not": {"enum": [0]}},
            "subsample": {"not": {"enum": [1.0]}},
            "boosting_type": {"not": {"enum": ["goss"]}},
        },
    }
    s2 = {
        "type": "object",
        "properties": {"subsample_freq": {"not": {}}, "subsample": {"not": {}}},
    }

    assert not isSubschema(s1, s2)


def test_68():
    s1 = {
        "type": "object",
        "properties": {"subsample_freq": {"not": {}}, "subsample": {"not": {}}},
    }
    s2 = {
        "type": "object",
        "properties": {"boosting_type": {"not": {"enum": ["rf", "goss"]}}},
    }

    assert not isSubschema(s1, s2)


def test_69():
    s1 = {
        "type": "object",
        "properties": {"subsample_freq": {"not": {}}, "subsample": {"not": {}}},
    }
    s2 = {
        "type": "object",
        "properties": {
            "boosting_type": {"not": {"enum": ["rf"]}},
            "subsample_freq": {"enum": [0]},
            "subsample": {"enum": [1.0]},
        },
    }

    assert not isSubschema(s1, s2)


def test_70():
    s1 = {
        "type": "object",
        "properties": {"subsample_freq": {"not": {}}, "subsample": {"not": {}}},
    }
    s2 = {
        "type": "object",
        "properties": {
            "subsample_freq": {"not": {"enum": [0]}},
            "subsample": {"not": {"enum": [1.0]}},
            "boosting_type": {"not": {"enum": ["goss"]}},
        },
    }

    assert not isSubschema(s1, s2)


def test_71():
    s1 = {
        "type": "object",
        "properties": {
            "boosting_type": {"enum": ["gbdt", "dart"]},
            "max_depth": {
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 50,
                "maximumForOptimizer": 500,
            },
            "min_child_samples": {
                "default": 20,
                "type": "integer",
                "minimumForOptimizer": 1,
                "maximumForOptimizer": 20,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimum": 0.0,
                "exclusiveMinimum": True,
                "minimumForOptimizer": 0.1,
                "maximum": 1.0,
            },
            "subsample_freq": {
                "default": 0,
                "type": "integer",
                "minimumForOptimizer": 0,
                "maximumForOptimizer": 10,
            },
        },
        "additionalProperties": False,
        "required": [
            "min_child_samples",
            "max_depth",
            "n_estimators",
            "subsample_freq",
            "boosting_type",
            "subsample",
            "learning_rate",
        ],
    }
    s2 = {
        "type": "object",
        "properties": {
            "boosting_type": {"enum": ["gbdt", "dart", "rf"]},
            "max_depth": {
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 50,
                "maximumForOptimizer": 500,
            },
            "min_child_samples": {
                "default": 20,
                "type": "integer",
                "minimumForOptimizer": 1,
                "maximumForOptimizer": 20,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimum": 0.0,
                "exclusiveMinimum": True,
                "minimumForOptimizer": 0.1,
                "maximum": 1.0,
                "exclusiveMaximum": True,
            },
            "subsample_freq": {
                "allOf": [
                    {
                        "default": 0,
                        "type": "integer",
                        "minimumForOptimizer": 0,
                        "exclusiveMinimumForOptimizer": True,
                        "maximumForOptimizer": 10,
                    },
                    {"not": {"enum": [0]}},
                ]
            },
        },
        "additionalProperties": False,
        "required": [
            "min_child_samples",
            "max_depth",
            "n_estimators",
            "subsample_freq",
            "boosting_type",
            "subsample",
            "learning_rate",
        ],
    }

    assert not isSubschema(s1, s2)


def test_72():
    s1 = {
        "type": "object",
        "properties": {
            "boosting_type": {"enum": ["gbdt", "dart", "rf"]},
            "max_depth": {
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 50,
                "maximumForOptimizer": 500,
            },
            "min_child_samples": {
                "default": 20,
                "type": "integer",
                "minimumForOptimizer": 1,
                "maximumForOptimizer": 20,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimum": 0.0,
                "exclusiveMinimum": True,
                "minimumForOptimizer": 0.1,
                "maximum": 1.0,
                "exclusiveMaximum": True,
            },
            "subsample_freq": {
                "allOf": [
                    {
                        "default": 0,
                        "type": "integer",
                        "minimumForOptimizer": 0,
                        "exclusiveMinimumForOptimizer": True,
                        "maximumForOptimizer": 10,
                    },
                    {"not": {"enum": [0]}},
                ]
            },
        },
        "additionalProperties": False,
        "required": [
            "min_child_samples",
            "max_depth",
            "n_estimators",
            "subsample_freq",
            "boosting_type",
            "subsample",
            "learning_rate",
        ],
    }
    s2 = {
        "type": "object",
        "properties": {
            "boosting_type": {"enum": ["gbdt", "dart"]},
            "max_depth": {
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "learning_rate": {
                "default": 0.1,
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 1.0,
            },
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 50,
                "maximumForOptimizer": 500,
            },
            "min_child_samples": {
                "default": 20,
                "type": "integer",
                "minimumForOptimizer": 1,
                "maximumForOptimizer": 20,
            },
            "subsample": {
                "default": 1.0,
                "type": "number",
                "minimum": 0.0,
                "exclusiveMinimum": True,
                "minimumForOptimizer": 0.1,
                "maximum": 1.0,
            },
            "subsample_freq": {
                "default": 0,
                "type": "integer",
                "minimumForOptimizer": 0,
                "maximumForOptimizer": 10,
            },
        },
        "additionalProperties": False,
        "required": [
            "min_child_samples",
            "max_depth",
            "n_estimators",
            "subsample_freq",
            "boosting_type",
            "subsample",
            "learning_rate",
        ],
    }

    assert not isSubschema(s1, s2)


def test_73():
    s1 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {"enum": ["euclidean"]},
            "compute_full_tree": {"enum": ["auto"]},
            "linkage": {"enum": ["ward", "complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {"not": {}},
            "compute_full_tree": {"enum": ["auto"]},
            "linkage": {"enum": ["ward", "complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }

    assert not isSubschema(s1, s2)


def test_74():
    s1 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {"enum": ["euclidean"]},
            "compute_full_tree": {"enum": ["auto"]},
            "linkage": {"enum": ["ward", "complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {"not": {}},
            "compute_full_tree": {"type": "boolean"},
            "linkage": {"enum": ["ward", "complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }

    assert not isSubschema(s1, s2)


def test_75():
    s1 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {
                "enum": [
                    "euclidean",
                    "l1",
                    "l2",
                    "manhattan",
                    "cosine",
                    "precomputed",
                ]
            },
            "compute_full_tree": {"enum": ["auto"]},
            "linkage": {"enum": ["complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {"not": {}},
            "compute_full_tree": {"enum": ["auto"]},
            "linkage": {"enum": ["ward", "complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }

    assert not isSubschema(s1, s2)


def test_76():
    s1 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {
                "enum": [
                    "euclidean",
                    "l1",
                    "l2",
                    "manhattan",
                    "cosine",
                    "precomputed",
                ]
            },
            "compute_full_tree": {"enum": ["auto"]},
            "linkage": {"enum": ["complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {"not": {}},
            "compute_full_tree": {"type": "boolean"},
            "linkage": {"enum": ["ward", "complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }

    assert not isSubschema(s1, s2)


def test_77():
    s1 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {"enum": ["euclidean"]},
            "compute_full_tree": {"type": "boolean"},
            "linkage": {"enum": ["ward", "complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {"not": {}},
            "compute_full_tree": {"enum": ["auto"]},
            "linkage": {"enum": ["ward", "complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }

    assert not isSubschema(s1, s2)


def test_78():
    s1 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {"enum": ["euclidean"]},
            "compute_full_tree": {"type": "boolean"},
            "linkage": {"enum": ["ward", "complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {"not": {}},
            "compute_full_tree": {"type": "boolean"},
            "linkage": {"enum": ["ward", "complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }

    assert not isSubschema(s1, s2)


def test_79():
    s1 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {
                "enum": [
                    "euclidean",
                    "l1",
                    "l2",
                    "manhattan",
                    "cosine",
                    "precomputed",
                ]
            },
            "compute_full_tree": {"type": "boolean"},
            "linkage": {"enum": ["complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {"not": {}},
            "compute_full_tree": {"enum": ["auto"]},
            "linkage": {"enum": ["ward", "complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }

    assert not isSubschema(s1, s2)


def test_80():
    s1 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {
                "enum": [
                    "euclidean",
                    "l1",
                    "l2",
                    "manhattan",
                    "cosine",
                    "precomputed",
                ]
            },
            "compute_full_tree": {"type": "boolean"},
            "linkage": {"enum": ["complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {"not": {}},
            "compute_full_tree": {"type": "boolean"},
            "linkage": {"enum": ["ward", "complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }

    assert not isSubschema(s1, s2)


def test_81():
    s1 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {"not": {}},
            "compute_full_tree": {"enum": ["auto"]},
            "linkage": {"enum": ["ward", "complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {"enum": ["euclidean"]},
            "compute_full_tree": {"enum": ["auto"]},
            "linkage": {"enum": ["ward", "complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }

    assert isSubschema(s1, s2)


def test_82():
    s1 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            # "affinity": {"not": {}},
            "compute_full_tree": {"enum": ["auto"]},
            "linkage": {"enum": ["ward", "complete", "average", "single"]},
        },
        # },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }

    s2 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            # "affinity": {"enum": ["euclidean", "l1", "l2", "manhattan", "cosine", "precomputed"]},
            "compute_full_tree": {"enum": ["auto"]},
            "linkage": {"enum": ["complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }

    assert not isSubschema(s1, s2)


def test_83():
    s1 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {"not": {}},
            "compute_full_tree": {"enum": ["auto"]},
            "linkage": {"enum": ["ward", "complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {"enum": ["euclidean"]},
            "compute_full_tree": {"type": "boolean"},
            "linkage": {"enum": ["ward", "complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }

    assert not isSubschema(s1, s2)


def test_84():
    s1 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {"not": {}},
            "compute_full_tree": {"enum": ["auto"]},
            "linkage": {"enum": ["ward", "complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {
                "enum": [
                    "euclidean",
                    "l1",
                    "l2",
                    "manhattan",
                    "cosine",
                    "precomputed",
                ]
            },
            "compute_full_tree": {"type": "boolean"},
            "linkage": {"enum": ["complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }

    assert not isSubschema(s1, s2)


def test_85():
    s1 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {"not": {}},
            "compute_full_tree": {"enum": ["auto"]},
            "linkage": {"enum": ["ward", "complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {"forOptimizer": {"not": {}}, "type": "object"},
            "compute_full_tree": {"enum": ["auto"]},
            "linkage": {"enum": ["complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }

    assert not isSubschema(s1, s2)


def test_86():
    s1 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {"not": {}},
            "compute_full_tree": {"enum": ["auto"]},
            "linkage": {"enum": ["ward", "complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {"not": {}},
            "compute_full_tree": {"type": "boolean"},
            "linkage": {"enum": ["ward", "complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }

    assert not isSubschema(s1, s2)


def test_87():
    s1 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {"not": {}},
            "compute_full_tree": {"enum": ["auto"]},
            "linkage": {"enum": ["ward", "complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {"forOptimizer": False, "type": "object"},
            "compute_full_tree": {"type": "boolean"},
            "linkage": {"enum": ["complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }

    assert not isSubschema(s1, s2)


def test_88():
    s1 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {"forOptimizer": {"not": {}}, "type": "object"},
            "compute_full_tree": {"enum": ["auto"]},
            "linkage": {"enum": ["complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {"not": {}},
            "compute_full_tree": {"enum": ["auto"]},
            "linkage": {"enum": ["ward", "complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }

    assert not isSubschema(s1, s2)


def test_89():
    s1 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {"forOptimizer": {"not": {}}, "type": "object"},
            "compute_full_tree": {"enum": ["auto"]},
            "linkage": {"enum": ["complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {"not": {}},
            "compute_full_tree": {"type": "boolean"},
            "linkage": {"enum": ["ward", "complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }

    assert not isSubschema(s1, s2)


def test_90():
    s1 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {"not": {}},
            "compute_full_tree": {"type": "boolean"},
            "linkage": {"enum": ["ward", "complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {"enum": ["euclidean"]},
            "compute_full_tree": {"enum": ["auto"]},
            "linkage": {"enum": ["ward", "complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }

    assert not isSubschema(s1, s2)


def test_91():
    s1 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {"not": {}},
            "compute_full_tree": {"type": "boolean"},
            "linkage": {"enum": ["ward", "complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {
                "enum": [
                    "euclidean",
                    "l1",
                    "l2",
                    "manhattan",
                    "cosine",
                    "precomputed",
                ]
            },
            "compute_full_tree": {"enum": ["auto"]},
            "linkage": {"enum": ["complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }

    assert not isSubschema(s1, s2)


def test_92():
    s1 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {"not": {}},
            "compute_full_tree": {"type": "boolean"},
            "linkage": {"enum": ["ward", "complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {"enum": ["euclidean"]},
            "compute_full_tree": {"type": "boolean"},
            "linkage": {"enum": ["ward", "complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }

    assert isSubschema(s1, s2)


def test_93():
    s1 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {"not": {}},
            "compute_full_tree": {"type": "boolean"},
            "linkage": {"enum": ["ward", "complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {
                "enum": [
                    "euclidean",
                    "l1",
                    "l2",
                    "manhattan",
                    "cosine",
                    "precomputed",
                ]
            },
            "compute_full_tree": {"type": "boolean"},
            "linkage": {"enum": ["complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }

    assert not isSubschema(s1, s2)


def test_94():
    s1 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {"not": {}},
            "compute_full_tree": {"type": "boolean"},
            "linkage": {"enum": ["ward", "complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {"not": {}},
            "compute_full_tree": {"enum": ["auto"]},
            "linkage": {"enum": ["ward", "complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }

    assert not isSubschema(s1, s2)


def test_95():
    s1 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {"not": {}},
            "compute_full_tree": {"type": "boolean"},
            "linkage": {"enum": ["ward", "complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {"forOptimizer": {"not": {}}, "type": "object"},
            "compute_full_tree": {"enum": ["auto"]},
            "linkage": {"enum": ["complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }

    assert not isSubschema(s1, s2)


def test_96():
    s1 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {"not": {}},
            "compute_full_tree": {"type": "boolean"},
            "linkage": {"enum": ["ward", "complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {"forOptimizer": {"not": {}}, "type": "object"},
            "compute_full_tree": {"type": "boolean"},
            "linkage": {"enum": ["complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }

    assert not isSubschema(s1, s2)


def test_97():
    s1 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {"forOptimizer": {"not": {}}, "type": "object"},
            "compute_full_tree": {"type": "boolean"},
            "linkage": {"enum": ["complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {"not": {}},
            "compute_full_tree": {"enum": ["auto"]},
            "linkage": {"enum": ["ward", "complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }

    assert not isSubschema(s1, s2)


def test_98():
    s1 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {"forOptimizer": {"not": {}}, "type": "object"},
            "compute_full_tree": {"type": "boolean"},
            "linkage": {"enum": ["complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "n_clusters": {
                "default": 2,
                "type": "integer",
                "minimumForOptimizer": 2,
                "maximumForOptimizer": 8,
            },
            "affinity": {"not": {}},
            "compute_full_tree": {"type": "boolean"},
            "linkage": {"enum": ["ward", "complete", "average", "single"]},
        },
        "additionalProperties": False,
        "required": ["compute_full_tree"],
    }

    assert not isSubschema(s1, s2)


def test_99():
    s1 = {
        "type": "object",
        "properties": {
            "n_components": {"enum": [None, "mle"]},
            "whiten": {"default": False, "type": "boolean"},
            "svd_solver": {"enum": ["auto", "full"]},
        },
        "additionalProperties": False,
        "required": ["svd_solver", "n_components", "whiten"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "n_components": {"enum": [None, "mle"]},
            "whiten": {"default": False, "type": "boolean"},
            "svd_solver": {"enum": ["full"]},
        },
        "additionalProperties": False,
        "required": ["svd_solver", "n_components", "whiten"],
    }

    assert not isSubschema(s1, s2)


def test_100():
    s1 = {
        "type": "object",
        "properties": {
            "n_components": {"enum": [None, "mle"]},
            "whiten": {"default": False, "type": "boolean"},
            "svd_solver": {"enum": ["full"]},
        },
        "additionalProperties": False,
        "required": ["svd_solver", "n_components", "whiten"],
    }

    s2 = {
        "type": "object",
        "properties": {
            "n_components": {"enum": [None, "mle"]},
            "whiten": {"default": False, "type": "boolean"},
            "svd_solver": {"enum": ["auto", "full"]},
        },
        "additionalProperties": False,
        "required": ["svd_solver", "n_components", "whiten"],
    }

    assert isSubschema(s1, s2)


def test_101():
    s1 = {
        "type": "object",
        "properties": {
            "n_components": {"enum": [None, "mle"]},
            "whiten": {"default": False, "type": "boolean"},
            "svd_solver": {"enum": ["auto", "full"]},
        },
        "additionalProperties": False,
        "required": ["svd_solver", "n_components", "whiten"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "n_components": {"enum": [None, "mle"]},
            "whiten": {"default": False, "type": "boolean"},
            "svd_solver": {"enum": ["full"]},
        },
        "additionalProperties": False,
        "required": ["svd_solver", "n_components", "whiten"],
    }

    assert not isSubschema(s1, s2)


def test_102():
    s1 = {
        "type": "object",
        "properties": {
            "n_components": {"enum": [None, "mle"]},
            "whiten": {"default": False, "type": "boolean"},
            "svd_solver": {"enum": ["full"]},
        },
        "additionalProperties": False,
        "required": ["svd_solver", "n_components", "whiten"],
    }

    s2 = {
        "type": "object",
        "properties": {
            "n_components": {"enum": [None, "mle"]},
            "whiten": {"default": False, "type": "boolean"},
            "svd_solver": {"enum": ["auto", "full"]},
        },
        "additionalProperties": False,
        "required": ["svd_solver", "n_components", "whiten"],
    }

    assert isSubschema(s1, s2)


def test_103():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {
                "default": 0.9,
                "type": "number",
                "minimumForOptimizer": 1e-10,
                "maximumForOptimizer": 1.0,
            },
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {
                "default": 0.9,
                "type": "number",
                "minimumForOptimizer": 1e-10,
                "maximumForOptimizer": 1.0,
            },
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_104():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {
                "default": 0.9,
                "type": "number",
                "minimumForOptimizer": 1e-10,
                "maximumForOptimizer": 1.0,
            },
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {
                "default": 0.9,
                "type": "number",
                "minimumForOptimizer": 1e-10,
                "maximumForOptimizer": 1.0,
            },
            "presort": {"type": "boolean"},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_105():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {
                "default": 0.9,
                "type": "number",
                "minimumForOptimizer": 1e-10,
                "maximumForOptimizer": 1.0,
            },
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {
                "default": 0.9,
                "type": "number",
                "minimumForOptimizer": 1e-10,
                "maximumForOptimizer": 1.0,
            },
            "presort": {"type": "boolean"},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_106():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {
                "default": 0.9,
                "type": "number",
                "minimumForOptimizer": 1e-10,
                "maximumForOptimizer": 1.0,
            },
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {
                "default": 0.9,
                "type": "number",
                "minimumForOptimizer": 1e-10,
                "maximumForOptimizer": 1.0,
            },
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_107():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {
                "default": 0.9,
                "type": "number",
                "minimumForOptimizer": 1e-10,
                "maximumForOptimizer": 1.0,
            },
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {
                "default": 0.9,
                "type": "number",
                "minimumForOptimizer": 1e-10,
                "maximumForOptimizer": 1.0,
            },
            "presort": {"type": "boolean"},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_108():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {
                "default": 0.9,
                "type": "number",
                "minimumForOptimizer": 1e-10,
                "maximumForOptimizer": 1.0,
            },
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {
                "default": 0.9,
                "type": "number",
                "minimumForOptimizer": 1e-10,
                "maximumForOptimizer": 1.0,
            },
            "presort": {"type": "boolean"},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_109():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {
                "default": 0.9,
                "type": "number",
                "minimumForOptimizer": 1e-10,
                "maximumForOptimizer": 1.0,
            },
            "presort": {"type": "boolean"},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {
                "default": 0.9,
                "type": "number",
                "minimumForOptimizer": 1e-10,
                "maximumForOptimizer": 1.0,
            },
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_110():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {
                "default": 0.9,
                "type": "number",
                "minimumForOptimizer": 1e-10,
                "maximumForOptimizer": 1.0,
            },
            "presort": {"type": "boolean"},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {
                "default": 0.9,
                "type": "number",
                "minimumForOptimizer": 1e-10,
                "maximumForOptimizer": 1.0,
            },
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_111():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {
                "default": 0.9,
                "type": "number",
                "minimumForOptimizer": 1e-10,
                "maximumForOptimizer": 1.0,
            },
            "presort": {"type": "boolean"},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {
                "default": 0.9,
                "type": "number",
                "minimumForOptimizer": 1e-10,
                "maximumForOptimizer": 1.0,
            },
            "presort": {"type": "boolean"},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_112():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {
                "default": 0.9,
                "type": "number",
                "minimumForOptimizer": 1e-10,
                "maximumForOptimizer": 1.0,
            },
            "presort": {"type": "boolean"},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {
                "default": 0.9,
                "type": "number",
                "minimumForOptimizer": 1e-10,
                "maximumForOptimizer": 1.0,
            },
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_113():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {
                "default": 0.9,
                "type": "number",
                "minimumForOptimizer": 1e-10,
                "maximumForOptimizer": 1.0,
            },
            "presort": {"type": "boolean"},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {
                "default": 0.9,
                "type": "number",
                "minimumForOptimizer": 1e-10,
                "maximumForOptimizer": 1.0,
            },
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_114():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {
                "default": 0.9,
                "type": "number",
                "minimumForOptimizer": 1e-10,
                "maximumForOptimizer": 1.0,
            },
            "presort": {"type": "boolean"},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {
                "default": 0.9,
                "type": "number",
                "minimumForOptimizer": 1e-10,
                "maximumForOptimizer": 1.0,
            },
            "presort": {"type": "boolean"},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_115():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {"default": 0.9, "enum": [0.9]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {"default": 0.9, "enum": [0.9]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_116():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {"default": 0.9, "enum": [0.9]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {"default": 0.9, "enum": [0.9]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_117():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {"default": 0.9, "enum": [0.9]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {"default": 0.9, "enum": [0.9]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_118():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {
                "default": 0.9,
                "type": "number",
                "minimumForOptimizer": 1e-10,
                "maximumForOptimizer": 1.0,
            },
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {
                "default": 0.9,
                "type": "number",
                "minimumForOptimizer": 1e-10,
                "maximumForOptimizer": 1.0,
            },
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_119():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {"default": 0.9, "enum": [0.9]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {"default": 0.9, "enum": [0.9]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_120():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {"default": 0.9, "enum": [0.9]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {"default": 0.9, "enum": [0.9]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_121():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {"default": 0.9, "enum": [0.9]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {"default": 0.9, "enum": [0.9]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_122():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {
                "default": 0.9,
                "type": "number",
                "minimumForOptimizer": 1e-10,
                "maximumForOptimizer": 1.0,
            },
            "presort": {"type": "boolean"},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {
                "default": 0.9,
                "type": "number",
                "minimumForOptimizer": 1e-10,
                "maximumForOptimizer": 1.0,
            },
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_123():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {
                "default": 0.9,
                "type": "number",
                "minimumForOptimizer": 1e-10,
                "maximumForOptimizer": 1.0,
            },
            "presort": {"type": "boolean"},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {
                "default": 0.9,
                "type": "number",
                "minimumForOptimizer": 1e-10,
                "maximumForOptimizer": 1.0,
            },
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_124():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {"default": 0.9, "enum": [0.9]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {"default": 0.9, "enum": [0.9]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_125():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {"default": 0.9, "enum": [0.9]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {"default": 0.9, "enum": [0.9]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_126():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {"default": 0.9, "enum": [0.9]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {"default": 0.9, "enum": [0.9]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_127():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {
                "default": 0.9,
                "type": "number",
                "minimumForOptimizer": 1e-10,
                "maximumForOptimizer": 1.0,
            },
            "presort": {"type": "boolean"},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {
                "default": 0.9,
                "type": "number",
                "minimumForOptimizer": 1e-10,
                "maximumForOptimizer": 1.0,
            },
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_128():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {
                "default": 0.9,
                "type": "number",
                "minimumForOptimizer": 1e-10,
                "maximumForOptimizer": 1.0,
            },
            "presort": {"type": "boolean"},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {
                "default": 0.9,
                "type": "number",
                "minimumForOptimizer": 1e-10,
                "maximumForOptimizer": 1.0,
            },
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_129():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {
                "default": 0.9,
                "type": "number",
                "minimumForOptimizer": 1e-10,
                "maximumForOptimizer": 1.0,
            },
            "presort": {"type": "boolean"},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {
                "default": 0.9,
                "type": "number",
                "minimumForOptimizer": 1e-10,
                "maximumForOptimizer": 1.0,
            },
            "presort": {"type": "boolean"},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_130():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {"default": 0.9, "enum": [0.9]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {"default": 0.9, "enum": [0.9]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_131():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {"default": 0.9, "enum": [0.9]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {"default": 0.9, "enum": [0.9]},
            "presort": {"enum": ["auto"]},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)


def test_132():
    s1 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {"default": 0.9, "enum": [0.9]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {
                "type": "integer",
                "minimumForOptimizer": 5,
                "maximumForOptimizer": 10,
            },
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }
    s2 = {
        "type": "object",
        "properties": {
            "loss": {"enum": ["ls", "lad", "huber", "quantile"]},
            "n_estimators": {
                "default": 100,
                "type": "integer",
                "minimumForOptimizer": 10,
                "maximumForOptimizer": 100,
            },
            "min_samples_split": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "min_samples_leaf": {
                "type": "number",
                "minimumForOptimizer": 0.01,
                "maximumForOptimizer": 0.5,
            },
            "max_depth": {
                "default": 3,
                "type": "integer",
                "minimumForOptimizer": 3,
                "maximumForOptimizer": 5,
            },
            "max_features": {"enum": ["auto", "sqrt", "log2", None]},
            "alpha": {"default": 0.9, "enum": [0.9]},
            "presort": {"type": "boolean"},
            "n_iter_no_change": {"enum": [None]},
            "tol": {
                "default": 0.0001,
                "type": "number",
                "minimumForOptimizer": 1e-08,
                "maximumForOptimizer": 0.01,
            },
        },
        "additionalProperties": False,
        "required": ["presort"],
    }

    assert not isSubschema(s1, s2)
