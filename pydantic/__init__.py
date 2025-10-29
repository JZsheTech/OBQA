"""Minimal stub of the pydantic API used for milestone scaffolding."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional


class _Undefined:
    pass


UNDEFINED = _Undefined()


class FieldInfo:
    def __init__(
        self,
        default: Any = UNDEFINED,
        *,
        default_factory: Optional[Callable[[], Any]] = None,
        **metadata: Any,
    ) -> None:
        self.default = default
        self.default_factory = default_factory
        self.metadata = metadata


def Field(default: Any = UNDEFINED, **kwargs: Any) -> FieldInfo:
    """Return metadata describing a field."""

    default_factory = kwargs.pop("default_factory", None)
    return FieldInfo(default=default, default_factory=default_factory, **kwargs)


def root_validator(pre: bool = False) -> Callable[[Callable[..., Dict[str, Any]]], Callable[..., Dict[str, Any]]]:
    """Decorator collecting validator functions to run after model init."""

    def decorator(func: Callable[..., Dict[str, Any]]):
        func.__is_root_validator__ = True  # type: ignore[attr-defined]
        func.__root_validator_pre__ = pre  # type: ignore[attr-defined]
        return func

    return decorator


class BaseModelMeta(type):
    def __new__(mcls, name: str, bases: tuple[type, ...], namespace: Dict[str, Any]):
        annotations: Dict[str, Any] = namespace.get("__annotations__", {})
        field_defaults: Dict[str, FieldInfo] = {}
        root_validators: List[Callable[..., Dict[str, Any]]] = []

        for attr_name, attr_value in list(namespace.items()):
            if isinstance(attr_value, FieldInfo):
                field_defaults[attr_name] = attr_value
                namespace[attr_name] = (
                    attr_value.default if attr_value.default is not UNDEFINED else None
                )
            elif callable(attr_value) and getattr(attr_value, "__is_root_validator__", False):
                root_validators.append(attr_value)

        namespace["__field_defaults__"] = field_defaults
        namespace["__root_validators__"] = root_validators
        namespace.setdefault("__annotations__", annotations)
        return super().__new__(mcls, name, bases, namespace)


class BaseModel(metaclass=BaseModelMeta):
    """Very small subset of the pydantic BaseModel API."""

    __annotations__: Dict[str, Any]
    __field_defaults__: Dict[str, FieldInfo]
    __root_validators__: List[Callable[..., Dict[str, Any]]]

    def __init__(self, **data: Any) -> None:
        for name in self.__annotations__:
            if name in data:
                value = data[name]
            elif name in self.__field_defaults__:
                field_info = self.__field_defaults__[name]
                if field_info.default_factory is not None:
                    value = field_info.default_factory()
                elif field_info.default is not UNDEFINED:
                    value = field_info.default
                else:
                    value = None
            else:
                value = getattr(self.__class__, name, None)
            setattr(self, name, value)

        for name, value in data.items():
            if name not in self.__annotations__:
                setattr(self, name, value)

        self.__post_init__()

    def __post_init__(self) -> None:
        for validator in self.__root_validators__:
            result = validator(self.__class__, self.__dict__.copy())
            if isinstance(result, dict):
                for key, value in result.items():
                    setattr(self, key, value)

    def model_dump(self) -> Dict[str, Any]:
        return {name: getattr(self, name) for name in self.__annotations__}

    def __repr__(self) -> str:  # pragma: no cover - diagnostic helper
        params = ", ".join(f"{k}={getattr(self, k)!r}" for k in self.__annotations__)
        return f"{self.__class__.__name__}({params})"
