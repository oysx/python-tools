import ast
import builtins
import contextlib
import inspect
import io
import mock
import re
import requests
import sys
import walrus
from spur.results import ExecutionResult
from mock import patch, PropertyMock, Mock
from functools import wraps


def dummy():
    pass


class PFLAG(object):
    ENABLE_MOCK_BASE_CLASSES = 1 << 0
    DISABLE_MOCK_NON_ATLAS_MODULES = 1 << 1
    FORCE_USE_INSTANCE_ATTRIBUTE = 1 << 2


class _patch(mock.mock._patch):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__exit_done__ = False

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.__exit_done__:
            return

        self.__exit_done__ = True
        return super().__exit__(exc_type, exc_val, exc_tb)


def _patch_object(
        target, attribute, new=mock.DEFAULT, spec=None,
        create=False, spec_set=None, autospec=None,
        new_callable=None, **kwargs
    ):
    getter = lambda: target
    return _patch(
        getter, attribute, new, spec, create,
        spec_set, autospec, new_callable, kwargs
    )


class PatchCompatible(object):
    attribute_name = None
    new = mock.DEFAULT

    def __init__(self, *args, **kwargs):
        self.dummy_mocker = patch(dummy.__module__ + '.' + dummy.__name__)\

    def __call__(self, fn):
        if hasattr(fn, 'patchings'):
            # has been patched before
            fn.patchings.append(self)
            return fn

        @wraps(fn)
        def wrapper(*args, **kwargs):
            with self.dummy_mocker.decoration_helper(wrapper, args, kwargs) as (newargs, newkwargs):
                return fn(*newargs, **newkwargs)

        # These 2 attributes are set to make itself recognizable by the pytest fixture mechanism
        wrapper.__wrapped__ = fn
        wrapper.patchings = [self]
        return wrapper


class PatchAll(PatchCompatible):
    #
    # attribute_name = None
    # new = mock.DEFAULT
    patcher_list = {}

    def __init__(self, modules_or_classes,
                 ignore=None, extra_include=None, return_value=None, filter_func=None, property_checker=None,
                 option=0):
        super(PatchAll, self).__init__()
        self.modules_or_classes = modules_or_classes
        self.ignore = ignore if ignore else []
        self.extra_include = extra_include if extra_include else []
        self.exit_stack = contextlib.ExitStack()
        self.mockers = {}
        self.mapper = {}
        self.patcher = []
        self.option = option
        self.sub_patchers = {}
        self.return_value = return_value if return_value else {}
        self.filter = filter_func if filter_func else self.filter_default
        self.property_checker = property_checker if property_checker else self.property_checker_default

    def __enter__(self):
        return self.patch()

    def __exit__(self, *args):
        return self.unpatch(*args)

    def unpatch(self, *args):
        self.exit_stack.__exit__(*args)

        self.patcher.reverse()
        for patcher in self.patcher:
            try:
                next(patcher)
            except StopIteration:
                pass

    # def __call__(self, fn):
    #     if hasattr(fn, 'patchings'):
    #         # has been patched before
    #         fn.patchings.append(self)
    #         return fn
    #
    #     @wraps(fn)
    #     def wrapper(*args, **kwargs):
    #         with self.dummy_mocker.decoration_helper(wrapper, args, kwargs) as (newargs, newkwargs):
    #             return fn(*newargs, **newkwargs)
    #
    #     # These 2 attributes are set to make itself recognizable by the pytest fixture mechanism
    #     wrapper.__wrapped__ = fn
    #     wrapper.patchings = [self]
    #     return wrapper

    @staticmethod
    def unmock(mocker):
        patcher = PatchAll.patcher_list.get(mocker)
        patcher.__exit__(None, None, None)

    def patch(self):
        if isinstance(self.modules_or_classes, dict):
            for k, v in self.modules_or_classes.items():
                self.mapper[v] = k
            self.modules_or_classes = list(self.modules_or_classes.values())
        else:
            if not isinstance(self.modules_or_classes, list):
                self.modules_or_classes = [self.modules_or_classes]
            for module_or_class in self.modules_or_classes:
                self.mapper[module_or_class] = module_or_class.__module__ + '.' + module_or_class.__name__ \
                    if inspect.isclass(module_or_class) else module_or_class.__name__

        try:
            for module_or_class in self.modules_or_classes:
                if not inspect.isclass(module_or_class) and not inspect.ismodule(module_or_class):
                    raise TypeError('Expected a module or class, got {}'.format(type(module_or_class)))

                targets = self.filter(module_or_class)
                ignore = self.ignore if isinstance(self.ignore, list) else self.ignore[self.mapper[module_or_class]]
                targets = [name for name in targets if name not in ignore]
                patcher = self.patch_recursive(module_or_class, targets)
                next(patcher)
                self.patcher.append(patcher)

            self.mockers['local'] = {}
            for e in self.extra_include:    # include both local import and super().selves
                p = patch(e)
                mocker = self.exit_stack.enter_context(p)
                self.mockers['local'][e] = mocker
        except:
            # invoke unpatch() manually since the exception in the __enter__() will not cause invoking of __exit__()
            if not self.unpatch(*sys.exc_info()):
                raise

        # remove empty entries
        removable = [k for k, v in self.mockers.items() if not v]
        [self.mockers.pop(k) for k in removable]

        if len(self.mockers) == 1:
            self.mockers = next(iter(self.mockers.values()))
        return self.mockers

    def patch_recursive(self, module_or_class, names):
        name = names[0]
        obj = getattr(module_or_class, name)
        new_callable = self.property_checker(obj)

        kw = {}
        if new_callable:
            kw.update({'new_callable': new_callable})
        if name in self.return_value:
            kw.update({'return_value': self.return_value[name]})

        patcher = _patch_object(module_or_class, name, **kw)
        with patcher as mocker:
            self.patcher_list[mocker] = patcher
            key = self.mapper[module_or_class]
            if key not in self.mockers:
                self.mockers[key] = {}
            self.mockers[key][name] = mocker
            if len(names) > 1:
                yield from self.patch_recursive(module_or_class, names[1:])
                pass
            else:
                if inspect.isclass(module_or_class) and (self.option & PFLAG.FORCE_USE_INSTANCE_ATTRIBUTE):
                    with patch.object(module_or_class, '__getattribute__', new=get_attribute_from_instance(module_or_class.__getattribute__)):
                        yield mocker
                else:
                    yield mocker

    def checker(self, obj, builtin=True, disable_mock_non_vivi_module=False):
        checker = not isinstance(obj, (int, float, str, bytes, tuple, list, dict, set, frozenset, type(None)))
        if not builtin:
            checker = checker and not (inspect.isclass(obj) and obj.__module__ == 'builtins')
            checker = checker and not (hasattr(obj, "__class__") and obj.__class__.__module__ == '__future__')
        if disable_mock_non_vivi_module:
            checker = checker and not self.is_non_vivi_module(obj)
        return checker

    def is_non_vivi_module(self, obj):
        return inspect.ismodule(obj) and not obj.__package__.startswith('vivi_framework')

    def property_checker_default(self, obj):
        return PropertyMock if inspect.isgetsetdescriptor(obj) or inspect.isdatadescriptor(obj) else None

    def filter_default(self, module_or_class):
        is_class = inspect.isclass(module_or_class)
        total = dir(module_or_class) if (self.option & PFLAG.ENABLE_MOCK_BASE_CLASSES) else module_or_class.__dict__
        targets = [name for name in total if not name.startswith('__') and not name.endswith('__')]
        targets = [name for name in targets if self.checker(getattr(module_or_class, name), builtin=is_class, disable_mock_non_vivi_module=(self.option & PFLAG.DISABLE_MOCK_NON_VIVI_MODULES))]
        return targets


class PatchGroup(PatchCompatible):

    def __init__(self, patches):
        super(PatchGroup, self).__init__()
        self.patches = patches
        self.exit_stack = contextlib.ExitStack()
        self.mockers = {}

    def __enter__(self):
        for n in self.patches:
            p = patch(n)
            m = self.exit_stack.enter_context(p)
            self.mockers[n] = m

        return self.mockers

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.exit_stack.__exit__(exc_type, exc_val, exc_tb)


def filter_for_properties(cls):
    targets = [name for name in dir(cls) if
                inspect.isgetsetdescriptor(get_real_attribute(cls, name)) or inspect.isdatadescriptor(get_real_attribute(cls, name))]
    return targets


def get_real_attribute(obj, name):
    for cls in obj.__mro__:
        try:
            result = object.__getattribute__(cls, name)
            return result
        except Exception:
            pass


def get_attribute_from_instance(wrapped):
    def wrapper(self, name):
        try:
            result = object.__getattribute__(self, '__dict__')[name]
            return result
        except Exception:
            pass

        return wrapped(self, name)

    return wrapper


def get_real_module(self_module, node):
    mod = [node.module] if node.module else []
    prefix = self_module.split('.')[:-node.level]
    mod = '.'.join(prefix + mod)
    return mod


def find_import(self_module, node):
    if isinstance(node, ast.ImportFrom):
        for name in node.names:
            asname = name.asname if name.asname else name.name
            return {asname: (get_real_module(self_module, node), name.name, node)}
    elif isinstance(node, ast.Import):
        for name in node.names:
            asname = name.asname if name.asname else name.name
            return {asname: (name.name, None, node)}



class AstParser(object):
    def __init__(self, node, mod=None):
        self.node = node
        self.module = mod
        self.new_locals = {}
        self.local_imports = {}
        self.external_references = {}
        self.builtin_references = {}
        self.args = {}
        self.myself = {}
        self.mysuper = {}

    def check_end_of_attribute(self, statement, expr, children):
        if isinstance(statement, ast.Attribute):
            children.append(expr)

    def parse_statement_with_dedup(self, statement, origin=False):
        expr, value = self.parse_statement(statement, origin=origin)
        value.remove(expr) if expr in value else None
        return expr, value

    def parse_attribute(self, statement):
        expr, value = self.parse_statement_with_dedup(statement.value)
        name = '.'.join((expr, statement.attr))
        return name, value

    def parse_assign(self, statement):
        values = []

        expr, value = self.parse_statement(statement.value)
        values.extend(value)
        self.check_end_of_attribute(statement.value, expr, values)
        for target in statement.targets:
            if isinstance(target, ast.Name):
                if not self.new_locals.get(target.id, None):
                    self.new_locals[target.id] = []
                self.new_locals[target.id].append((expr, value))
            else:
                expr, value = self.parse_statement(target)
                values.extend(value)
                self.check_end_of_attribute(target, expr, values)
        return None, values

    def parse_call(self, statement):
        value = []
        func, children = self.parse_statement_with_dedup(statement.func)
        func = func + "()"
        _, args = self.parse_statement(statement.args)
        _, keywords = self.parse_statement(statement.keywords)
        if func == 'getattr()':
            obj, children = self.parse_statement_with_dedup(statement.args[0], origin=True)
            value.extend(children)
            att, children = self.parse_statement_with_dedup(statement.args[1], origin=True)
            value.extend(children)
            replacement = '.'.join([obj, att])
            value.append(replacement)   # here we add it into list since it could not be inserted in the upper layer
            return replacement, value

        value.extend(children)
        if func != 'super()':     # do not add argument references for super() call
            value.extend(args)
            value.extend(keywords)

        value.append(func)
        return func, value

    def parse_list(self, statement, stype=list, names=None):
        if not names:
            names = [None] * len(statement)

        get_expr = {
            ast.List: ('[]', None),
            ast.Dict: ('{}', None),
            ast.Tuple: ('()', None),
            ast.Set: ('()', None),
            ast.Subscript: ('[]', 'value'),
        }
        value = []
        exprs = {}
        for i, s in enumerate(statement):
            expr, children = self.parse_statement(s)
            value.extend(children)
            self.check_end_of_attribute(s, expr, value)
            exprs[names[i]] = expr

        expr_ret = get_expr.get(stype, (None, None))
        expr_ret = expr_ret[0] if not expr_ret[1] else exprs.get(expr_ret[1], '') + expr_ret[0]
        return expr_ret, value

    def parse_import(self, statement):
        result = find_import(self.module, statement)
        name, mod, attr = [(k, v[0], v[1]) for k, v in result.items()][0]
        self.local_imports[name] = (mod, attr)
        return (None, [])

    def parse_statement(self, statement, origin=False):
        if isinstance(statement, list):
            return self.parse_list(statement)
        elif isinstance(statement, ast.Name):
            return (statement.id, [statement.id])
        elif isinstance(statement, ast.Str):
            return ('str', ['str']) if not origin else (statement.s, [statement.s])
        elif isinstance(statement, ast.Import) or isinstance(statement, ast.ImportFrom):
            return self.parse_import(statement)
        elif isinstance(statement, ast.Num):
            return (None, []) #('num', ['num'])     #?????
        elif isinstance(statement, ast.Assign):
            return self.parse_assign(statement)
        elif isinstance(statement, ast.Attribute):
            return self.parse_attribute(statement)
        elif isinstance(statement, ast.Call):
            return self.parse_call(statement)
        elif isinstance(statement, ast.AST):
            nodes = [getattr(statement, field) for field in statement._fields]
            return self.parse_list(nodes, type(statement), statement._fields)
        else:
            return (None, [])

    def record_access(self, value):
        if not value:
            return
        name = value.split('.')[0]
        if name not in self.external_references:
            self.external_references[name] = []
        self.external_references[name].append(value)

    def parse_function(self):
        expr, value = self.parse_statement(self.node.body)
        [self.record_access(v) for v in value]

        builtin_names = []
        for name in self.external_references:
            search = re.sub(r'\W', '', name)
            if self.is_builtin(search):
                builtin_names.append(name)
        for name in builtin_names:
            self.builtin_references.update({name: self.external_references.pop(name)})

        for arg in self.node.args.args + [self.node.args.kwarg, self.node.args.vararg]:
            if arg:
                self.args[arg.arg] = self.external_references.pop(arg.arg, [])

        if self.node.args.args:
            name = self.node.args.args[0].arg
            self.myself[name] = self.args.pop(name)
            excludes = ['.'.join([name, n]) for n in ['__name__', '__module__', '__doc__', '__dict__', '__weakref__']]
            [self.myself[name].remove(e) for e in excludes if e in self.myself[name]]   # remove some special attributes which can not be mocked

        if 'super()' in self.builtin_references:
            self.mysuper['super()'] = self.builtin_references.pop('super()')

        return self.collect_possible_mocks()

    def collect_possible_mocks(self):
        mocks = {}
        # consume locals
        mocks.update(self.myself)
        mocks.update(self.mysuper)
        mocks.update(self.args)
        mocks.update(self.builtin_references)
        # self.new_locals = {k: set(v) for k, v in self.new_locals.items()}   #uniq
        self.consume_locals(mocks, self.external_references)

        # uniq
        for k, v in mocks.items():
            mocks[k] = set(v)

        args = {k: v for k, v in mocks.items() if k in self.args}
        print("Arguments: {}".format(args))

        builtins = {k: v for k, v in mocks.items() if k in self.builtin_references}
        print("Builtins: {}".format(builtins))

        myself = {k: ['.'.join(r.split('.')[1:]) for r in v] for k, v in mocks.items() if k in self.myself}
        print("CLASS: {}".format(myself))

        mysuper = {k: [re.sub(r'^.+?\.', '', r) for r in v] for k, v in mocks.items() if k in self.mysuper}
        print("SUPER: {}".format(mysuper))

        externals = {k: v for k, v in mocks.items()
                     if k not in self.args.keys()
                     and k not in self.builtin_references.keys()
                     and k not in self.myself.keys()
                     and k not in self.mysuper.keys()
                     and k not in self.local_imports.keys()
                     and re.sub(r'\W', '', k)   # strip those native types such as dict which is represented as '{}'
                     }
        # externals = {k: re.sub(r'^.+?\.', '', r) for k, r in externals.items()}
        externals = {k: ['.'.join(r.split('.')[1:]) for r in v] for k, v in externals.items()}
        print("EXTERNALS: {}".format(externals))

        mocks = {}
        myself = list(iter(myself.values()))
        myself = myself[0] if myself else []
        mysuper = list(iter(mysuper.values()))
        mysuper = mysuper[0] if mysuper else []
        mocks['class'] = set([re.sub(r'\W*\..*$|\W*$', '', v) for v in myself if v])    # strip attribute tailer or function call string '()'
        mocks['super'] = set([re.sub(r'\W*\..*$|\W*$', '', v) for v in mysuper])
        mocks['external'] = {re.sub(r'\W', '', k): [re.sub(r'\W*\..*$|\W*$', '', r) for r in v] for k, v in externals.items()}
        mocks['local_import'] = set(['.'.join(v) for v in self.local_imports.values()])
        return mocks

    def consume_locals(self, mocks, obj):
        for name, refers in obj.items():
            if name not in self.new_locals:
                if not mocks.get(name, None):
                    mocks[name] = []
                mocks[name].extend(refers)
                continue

            for e in self.new_locals[name]:
                value = e[0]
                if not value:
                    if not e[1]:
                        continue
                    value = e[1][-1]
                temps = {value.split('.')[0]: [v.replace(name, value, 1) for v in refers]}
                self.consume_locals(mocks, temps)

    def is_builtin(self, name):
        return name in dir(builtins)


class FuncEnvFinder(object):
    def __init__(self, func):
        self.func = func
        self.filename = inspect.getsourcefile(func)
        self.self_node = None
        self.local_import_nodes = {}
        self.imports = {}
        self.imports_global = {}
        self.imports_self = {}
        self.imports_local_other = {}
        self.parser = None

    def get_real_module(self, node):
        mod = [node.module] if node.module else []
        prefix = self.func.__module__.split('.')[:-node.level]
        mod = '.'.join(prefix + mod)
        return mod

    def find_import(self, node):
        if isinstance(node, ast.ImportFrom):
            for name in node.names:
                asname = name.asname if name.asname else name.name
                self.imports[asname] = (self.get_real_module(node), name.name, node)
        elif isinstance(node, ast.Import):
            for name in node.names:
                asname = name.asname if name.asname else name.name
                self.imports[asname] = (name.name, None, node)

    def run(self):
        source = io.open(self.filename, "rb").read()
        pkg = ast.parse(source)
        for node in ast.walk(pkg):
            if isinstance(node, ast.FunctionDef):
                if node.name == self.func.__name__:
                    self.self_node = node

                local_import_nodes = [n for n in ast.walk(node) if isinstance(n, (ast.Import, ast.ImportFrom))]
                if local_import_nodes:
                    self.local_import_nodes[node] = local_import_nodes
            self.find_import(node)

        self.collect_imports()
        self.parser = AstParser(self.self_node, self.func.__module__)
        return self.parser.parse_function()

    def show_imports(self):
        print(self.imports_self)
        print(self.imports_global)

    def collect_imports(self):
        for k, v in self.imports.items():
            node = v[2]
            self_imports = self.local_import_nodes.get(self.self_node, [])
            all_func_imports = []
            [all_func_imports.extend(v) for v in self.local_import_nodes.values()]
            if node in all_func_imports:
                if node in self_imports:
                    self.imports_self[k] = v[:2]
                else:
                    self.imports_local_other[k] = v[:2]
                continue
            self.imports_global[k] = v[:2]


def static_object(cls_or_obj, **data):
    model_obj = cls_or_obj() if inspect.isclass(cls_or_obj) else cls_or_obj
    property_names = filter_for_properties(model_obj.__class__)
    obj_dict = object.__getattribute__(model_obj, '__dict__')
    for name in property_names:
        if name in data:
            obj_dict[name] = data[name]

    return model_obj


def patch_model_fields(model_cls):
    def filter_for_fields(cls):
        targets = [name for name in dir(cls) if isinstance(getattr(cls, name), walrus.Field)]
        return targets

    return PatchAll(model_cls, filter_func=filter_for_fields)


def patch_model_properties(model_cls, ignore=None, **kwargs):
    return_value = kwargs
    return PatchAll(model_cls, filter_func=filter_for_properties, return_value=return_value, ignore=ignore, option=PFLAG.FORCE_USE_INSTANCE_ATTRIBUTE)


def patch_all_attributes(modules_or_classes,
                         ignore=None, extra_include=None,
                         return_value=None, filter_func=None,
                         property_checker=None, option=0):
    return PatchAll(modules_or_classes,
                    ignore=ignore, extra_include=extra_include,
                    return_value=return_value, filter_func=filter_func,
                    property_checker=property_checker, option=option)


def patch_target_references(container, func, ignore=None):
    func = getattr(container, func)
    finder = FuncEnvFinder(func)
    mocks = finder.run()

    cls = bases = None
    if inspect.isclass(container):
        cls = container
        bases = [c for c in container.__mro__][1:-1]
    mod = sys.modules[func.__module__]

    mypatch = []
    mypatch.extend(['.'.join([cls.__module__, cls.__name__, name]) for name in mocks.get('class', [])])
    mypatch.extend(mocks.get('local_import', []))
    for cls in bases:
        mypatch.extend(['.'.join([cls.__module__, cls.__name__, name]) for name in mocks.get('super', []) if hasattr(cls, name)])
    for k, v in mocks.get('external', {}).items():
        if '' in v:
            # mock external object itself
            mypatch.append('.'.join([mod.__name__, k]))
            continue

        mypatch.extend(['.'.join([mod.__name__, k, r]) for r in v])

    #uniq
    mypatch = list(set(mypatch))

    pt = PatchGroup(mypatch)
    return pt


def patch_target_environment(container, func, ignore=None):
    ignore = [] if not ignore else ignore
    cls = None
    mock_supers = []
    func = getattr(container, func)
    finder = FuncEnvFinder(func)
    finder.run()

    if inspect.isclass(container):
        # function defined in class
        cls = container

        # the module should be the file which the method reside in, not the class reside in since the method could
        # not reside in the class'es file but its base class file!!!
        # mod = sys.modules[container.__module__]
        all_cls = [c for c in cls.__mro__ if func.__name__ in vars(c)]
        real_cls = all_cls[0]
        base_cls = all_cls[1:]
        mod = sys.modules[real_cls.__module__]
        mock_supers = ['.'.join([c.__module__, c.__name__, func.__name__]) for c in base_cls]
    elif inspect.ismodule(container):
        mod = container
    else:
        raise TypeError('Expected a module or class, got {}'.format(type(container)))

    extra_include = ['.'.join(v) for v in finder.imports_self.values() if v[1]] + mock_supers
    if cls:
        return PatchAll({'cls': cls, 'mod': mod}, ignore={'cls': [func.__name__]+ignore, 'mod': [cls.__name__]+ignore},
                        option=PFLAG.DISABLE_MOCK_NON_VIVI_MODULES | PFLAG.ENABLE_MOCK_BASE_CLASSES,
                        extra_include=extra_include)
    else:
        return PatchAll(mod, ignore=[func.__name__]+ignore, extra_include=extra_include)


class WalrusModelMocker(object):
    auto = False

    def patch_load(this):
        @classmethod
        def load(cls, *args, **kwargs):
            return cls()
        return load

    def patch_query(this):
        @classmethod
        def query(cls, *args, **kwargs):
            if this.auto:
                yield cls()

            return
        return query

def model_auto_gen():
    WalrusModelMocker.auto = True
    yield
    WalrusModelMocker.auto = False

def patch_walrus_model():
    walrus_model = WalrusModelMocker()
    with patch('walrus.models.Model.save'):
        with patch('walrus.models.Model.load', new=walrus_model.patch_load()):
            with patch('walrus.models.Model.query', new=walrus_model.patch_query()):
                with patch('walrus.models.Model.delete'):
                    yield

def redis_simulator():
    database = {}

    def redis_execute_command(self, cmd, *args, **kwargs):
        def INCRBY(key, value):
            data = database.get(key, None)
            if data is None:
                database[key] = 0
            database[key] += value
            return database[key]

        def HMSET(key, *args, **kwargs):
            data = database.get(key, None)
            if data is None:
                database[key] = {}
            for i in range(0, len(args), 2):
                database[key][args[i]] = args[i+1]

        def SADD(key, value):
            data = database.get(key, None)
            if data is None:
                database[key] = set()
            database[key].add(value)

        def ZADD(key, *args):
            data = database.get(key, None)
            if data is None:
                database[key] = set()
            for i in range(0, len(args), 2):
                database[key].add((args[i], args[i+1]))

        def ZRANGEBYLEX(key, min, max, *args, **kwargs):
            data = database.get(key, None)
            if data is None:
                return []

            min_ind, min = min[0], min[1:]
            max_ind, max = max[0], max[1:]
            result = []
            for score, value in data:
                if min_ind == '-' or (min_ind == '(' and value > min) or (min_ind == '[' and value >= min):
                    result.append(value)
                elif max_ind == '+' or (max_ind == ')' and value < max) or (max_ind == ']' and value <= max):
                    result.append(value)

            result = sorted(result)
            return result

        def SORT(key, *args, **kwargs):
            data = database.get(key, [])
            token = {}
            def _parse_args(a):
                if not a:
                    return
                elif isinstance(a[0], redis.connection.Token) and (a[0].value == 'BY' or a[0].value == 'STORE'):
                    token[a[0].value] = a[1]
                    _parse_args(a[2:])
                elif isinstance(a[0], redis.connection.Token) and (a[0].value == 'LIMIT'):
                    token[a[0].value] = a[1], a[2]
                    _parse_args(a[3:])
                elif isinstance(a[0], redis.connection.Token) and (a[0].value == 'GET'):
                    if not token.get('GET', None):
                        token['GET'] = []
                    token[a[0].value].append(a[1])
                    _parse_args(a[2:])
                elif isinstance(a[0], redis.connection.Token):
                    token[a[0].value] = True
                    _parse_args(a[1:])
            _parse_args(args)
            BY = token.get('BY', None)
            if BY:
                result = [(d, BY.replace('*', d)) for d in data]
                sorted(result, key=lambda x: database.get(x[1], ''), reverse=True)
                return [r[0] for r in result] if result else []

        response = {
            'ZRANGEBYLEX': ZRANGEBYLEX,
            'EXISTS': database.get(args[0], None) is not None,
            'SINTERSTORE': lambda dest, *args, **kwargs: database.get(),
            'INCRBY': INCRBY,
            'SORT': SORT,
            'DEL': lambda key: database.pop(key, None),
            'HMSET': HMSET,
            'SADD': SADD,
            'ZADD': ZADD,
            'HGETALL': lambda key: database.get(key),
            'SSCAN': lambda key, cursor: (0, database.get(key, [])),
        }
        for k, v in response.items():
            if re.match(k, cmd):
                return v(*args, **kwargs) if inspect.isfunction(v) else v

    def redis_run_script(self, script, keys=None, args=None):
        response = {
            'lock_acquire': 1,
            'lock_release': 1,
        }
        return response.get(script, None)

    with patch("redis.client.StrictRedis.execute_command", new=redis_execute_command) as command:
        with patch('walrus.database.Database.run_script', new=redis_run_script) as run:
            yield
