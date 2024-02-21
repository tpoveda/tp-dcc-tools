from tp.bootstrap import log

logger = log.bootstrapLogger


def run_script_function(file_path, func_name, message, *args):
    """
    Runs a function in the given Python script.

    :param str file_path: absolute path to the Python script.
    :param str func_name: function name within the script to run.
    :param str message: debug message to print before the function is run.
    :param tuple args: arguments to pass to the function which will be executed.
    :return: function return value.
    :rtype: any
    """

    try:
        scope = dict()
        with open(file_path, 'rb') as f:
            exec(compile(f.read(), file_path, 'exec'), scope)
        func = scope.get(func_name)
        if func is not None:
            logger.debug(message)
            return func(*args)
    except Exception:
        logger.error(f'Problem loading {file_path}', exc_info=True)
