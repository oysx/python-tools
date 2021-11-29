from fake_module.fake_mod import fake_function_two, fake_function_one
from fake_module.fake_mod import FakeClassOne


def test_main():
    print("in test_main")
    fake_function_two()
    instance_one = FakeClassOne()
    instance_one.doit('OK')


if __name__ == "__main__":
    test_main()
    fake_function_one('KO')
