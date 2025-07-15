class HardwareError(Exception):
    """Базовое исключение для ошибок оборудования."""
    pass

# mirrors.py
class SerialConnectionError(HardwareError):
    """Ошибка при открытии COM-порта."""
    pass


class MirrorCommunicationError(HardwareError):
    """Ошибка при получении или установке позиции зеркал."""
    pass

# rigol_rw.py
class SignalGeneratorError(HardwareError):
    """Базовая ошибка генератора сигналов"""
    pass

class SignalParameterError(SignalGeneratorError):
    """Неправильные параметры настройки"""
    pass

class SignalConnectionError(SignalGeneratorError):
    """Ошибка подключения к генератору"""
    pass

# spincore
class SpinCoreError(HardwareError):
    """Базовое исключение для работы с платой SpinCore"""
    pass

class SpinCoreConnectionError(SpinCoreError):
    """Ошибка при подключении к DLL или инициализации"""
    pass

class SpinCoreExecutionError(SpinCoreError):
    """Ошибка выполнения вызовов SpinCore DLL"""
    pass

