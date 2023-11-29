class ProxyObject(object):
    OBJECT_NAME = '__atlas__obj__'
    CONSTRUCTOR_NAME = '__atlas__constructor__'

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

        self.new_obj = None
        self.customized_magic = []
        for name, method in vars(self.ProxyBase).items():
            if callable(method) or inspect.ismethoddescriptor(method):
                self.customized_magic.append(name)

    class ProxyBase(object):
        def __new__(cls, *args, **kwargs):
            return object.__new__(cls)

        def __init__(self, obj, constructor=None):
            object.__setattr__(self, ProxyObject.OBJECT_NAME, obj)
            object.__setattr__(self, ProxyObject.CONSTRUCTOR_NAME, constructor)

        def __getattribute__(self, item):
            if item in ['cache', 'lock']:
                real = object.__getattribute__(self, item)
                return real
            real = object.__getattribute__(self, ProxyObject.OBJECT_NAME)
            if real is None:
                real = object.__getattribute__(self, ProxyObject.CONSTRUCTOR_NAME)()
                object.__getattribute__(self, '__init__')(real)
            return real.__getattribute__(item)

        # def __setattr__(self, key, value):
        #     if key == ProxyObject.OBJECT_NAME:
        #         object.__setattr__(self, ProxyObject.OBJECT_NAME, value)
        #     return object.__setattr__(object.__getattribute__(self, ProxyObject.OBJECT_NAME), key, value)

    class ProxyMethod(object):
        def cache(self, *args, **kwargs):
            def invoke():
                real = object.__getattribute__(self, ProxyObject.OBJECT_NAME)
                return real.cache(*args, **kwargs)
            return ProxyObject().proxy(Cache, constructor=invoke)

        def lock(self, *args, **kwargs):
            def invoke():
                real = object.__getattribute__(self, ProxyObject.OBJECT_NAME)
                return real.lock(*args, **kwargs)
            return ProxyObject().proxy(Lock, constructor=invoke)

    def proxy_one(self, name):
        def proxy_func(this, *args, **kwargs):
            obj = object.__getattribute__(this, ProxyObject.OBJECT_NAME)
            if obj is None:
                obj = object.__getattribute__(this, ProxyObject.CONSTRUCTOR_NAME)()
                this.__init__(obj)
            return getattr(obj, name)(*args, **kwargs)

        return proxy_func

    def proxy(self, obj, owner=None, property_name=None, bases=None, constructor=None):
        bases = [] if not bases else bases
        proxied_magic = {}

        assert ((not isinstance(obj, type)) and constructor is None) or (isinstance(obj, type) and constructor is not None)

        cls = obj.__class__ if not isinstance(obj, type) else obj
        for name in dir(cls):
            if name.startswith('__') and name.endswith('__'):
                attr = getattr(cls, name, None)
                if not callable(attr):
                    continue
                if name not in self.customized_magic:
                    proxied_magic[name] = self.proxy_one(name)

        LOGGER.info("Setting up magic methods: %s", proxied_magic.keys())
        # assert '__getattribute__' in proxied_magic.keys()
        assert '__setattr__' in proxied_magic.keys()

        new_cls = type(object.__str__('AtlasProxy') + cls.__name__, (self.ProxyBase, *bases), proxied_magic)

        obj = None if isinstance(obj, type) else obj
        self.new_obj = new_cls(obj, constructor=constructor)
        subscribe = getattr(owner, '__atlas_register_propagating__', None) if owner else None
        if subscribe:
            # subscribe(property_name, self.update)
            subscribe(property_name, object.__getattribute__(self.new_obj, '__init__'))
        return self.new_obj

    def update(self, obj):
        LOGGER.info("Update from %s to %s", self.new_obj, obj)
        setattr(self.new_obj, ProxyObject.OBJECT_NAME, obj)
