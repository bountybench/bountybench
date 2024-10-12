from typing import Optional
from collections import defaultdict

#does it inherit from dict?
# given this is a singleton, make it do little work besides 
# in future rather than __get_tiem,mabye separate and just a single instruction because of multithreading
class ResourceDict():
    def __init__():
        self.id_to_resource = dict()
        self.resource_type_to_resources = defaultdict(list)

    def __get_item__(key):
        if key is a resource class:
            if self_resource_type_to_resources[key]:
                return self_resource_type_to_resources[key]
            return None
        # maybe check type of key, I think it a hashable
        elif if hashable:
            if key in id_to_resource:
                return.id_to_resource[key]
            else:
                return None
        else:
            raise Exception('unsupported type')

    """
    What exactly are we accomplishing here over just a dictionary.
    Maybe there's value in a dictionary that we call resourcemanager

    https://realpython.com/inherit-python-dict/#:~:text=In%20Python%2C%20you%20can%20do,the%20built%2Din%20dict%20class

    How to think about the task server vs agent env

    'name' of the resource?

    is a resource of type Browser there? how to do with dictionary

    access patterns:
        by name/id
            - this is necessary for cases of multiple task servers where you want to reach a specific server
        OR
        by resource type
            - this is useful for those when you jsut want any of this resource type (e.g. any kali linux work env or browser)

    in future:
        resources may have constaints, e.g. kali linux work env can only support x parallelism n cpu etc.
        say if resources are being used

        or even task server maybe can only support x api calls
    """
# Export globally / or maybe everyone can just import resource_dict. also mabye should make capital? 
resource_dict = ResourceDict()

"""
The design pattern you're referring to is the **Singleton Pattern**. In Python, the Singleton Pattern ensures that a class has only one instance and provides a global point of access to that instance. This is useful when exactly one object is needed to coordinate actions across the system.

---

## Singleton Pattern in Python

### What is a Singleton?

A Singleton is a class that allows only a single instance of itself to be created and provides a global point of access to it. In other words, no matter how many times you instantiate the Singleton class, you will always get the same instance.

### Implementing Singletons in Python

There are several ways to implement a Singleton pattern in Python. Here are some common approaches:

### 1. Using a Decorator

```python
def singleton(cls):
    """Decorator for making a class a Singleton."""
    instances = {}

    def wrapper(*args, **kwargs):
        if cls not in instances:
            print(f"Creating new instance of {cls.__name__}")
            instances[cls] = cls(*args, **kwargs)
        else:
            print(f"Using existing instance of {cls.__name__}")
        return instances[cls]

    return wrapper

@singleton
class GlobalSettings:
    def __init__(self):
        self.config = {}

# Usage
settings1 = GlobalSettings()
settings2 = GlobalSettings()
print(settings1 is settings2)  # Output: True
```

**Explanation:**

- The `singleton` decorator maintains a dictionary `instances` to store instances of classes.
- When the decorated class is instantiated, the decorator checks if an instance already exists.
- If it does, it returns the existing instance; otherwise, it creates a new one.

### 2. Using a Metaclass

```python
class SingletonMeta(type):
    """MetaClass for Singletons."""
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            print(f"Creating new instance of {cls.__name__}")
            cls._instances[cls] = super().__call__(*args, **kwargs)
        else:
            print(f"Using existing instance of {cls.__name__}")
        return cls._instances[cls]

class GlobalSettings(metaclass=SingletonMeta):
    def __init__(self):
        self.config = {}

# Usage
settings1 = GlobalSettings()
settings2 = GlobalSettings()
print(settings1 is settings2)  # Output: True
```

**Explanation:**

- `SingletonMeta` is a metaclass that overrides the `__call__` method.
- It maintains a class-level `_instances` dictionary.
- When a class with `SingletonMeta` as its metaclass is instantiated, it checks `_instances` to determine if an instance exists.

### 3. Using a Module-Level Singleton

Python modules are singletons by nature because the interpreter loads each module only once. You can leverage this behavior:

**my_singleton.py**

```python
class GlobalSettings:
    def __init__(self):
        self.config = {}

global_settings = GlobalSettings()
```

**Usage in other modules:**

```python
from my_singleton import global_settings

# Now, global_settings can be accessed from anywhere in your application.
global_settings.config['theme'] = 'dark'
```

**Explanation:**

- Define your singleton class in a module.
- Create an instance at the module level.
- Import the instance directly wherever you need it.

### 4. Using the Borg Pattern (Monostate)

The Borg pattern ensures that all instances share the same state, rather than enforcing only one instance.

```python
class Borg:
    _shared_state = {}

    def __init__(self):
        self.__dict__ = self._shared_state

class GlobalSettings(Borg):
    def __init__(self):
        super().__init__()
        if not hasattr(self, 'config'):
            self.config = {}

# Usage
settings1 = GlobalSettings()
settings2 = GlobalSettings()
settings1.config['theme'] = 'light'
print(settings2.config['theme'])  # Output: light
print(settings1 is settings2)     # Output: False
```

**Explanation:**

- All instances share the same `_shared_state`.
- Each instance's `__dict__` points to the `_shared_state`.
- Different instances, but they share the same state.

---

## Considerations When Using Singletons

### Advantages

- **Controlled Access to a Single Instance:** Useful for managing shared resources like configuration, logging, or thread pools.
- **Global Access Point:** The singleton instance can be accessed from anywhere, eliminating the need to pass the instance around.

### Disadvantages

- **Hidden Dependencies:** Global access can make dependencies less obvious, complicating testing and debugging.
- **Difficulty in Subclassing:** Singletons can be challenging to subclass in a meaningful way.
- **Concurrency Issues:** In multi-threaded applications, care must be taken to manage access to the singleton instance.

### Best Practices

- **Use Sparingly:** Limit the use of singletons to cases where they are genuinely needed.
- **Consider Alternatives:** Dependency injection can often replace the need for singletons.
- **Thread Safety:** Ensure that your singleton implementation is thread-safe if used in a multi-threaded context.

---

## Conclusion

The Singleton Pattern provides a way to ensure that a class has only one instance and to provide a global point of access to that instance. In Python, you can implement singletons using decorators, metaclasses, modules, or the Borg pattern, depending on your specific needs.

Remember to weigh the pros and cons before deciding to use a singleton, as they can introduce challenges in code maintainability and testing.

---

Feel free to ask if you need further clarification or assistance with implementing any of these patterns!
"""
