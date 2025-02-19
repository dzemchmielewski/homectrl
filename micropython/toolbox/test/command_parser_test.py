from command_parser import CommandParser

if __name__ == '__main__':

    def check(cp: CommandParser, input: str, expected: tuple):
        result = cp.parse(input, return_type=tuple)
        if result != expected:
            print(f"{'PASS' if result == expected else 'FAIL'} INPUT: >> {input} <<")
            print(f'\tExpected: {expected}')
            print(f'\t  Actual: {result}')
            print('')
        return result == expected

    cp = CommandParser({
        "help": None,
        "firmware": None,
        "bt": {
            "on": None,
            "off": None,
            "mac": None
        },
        "config": {
            "get": None,
            "set": {
                "sensitivity": [int, int, int],
                "threshold": [int, int, int],
                "mixed": [str, int, float]
            }
        },
        "stringtest": str,
        "inttest": int,
        "floattest": float
    })

    cases = [
        ("", (None, None, "Subcommand required: ['help', 'firmware', 'bt', 'config', 'stringtest', 'inttest', 'floattest']")),
        ("not_existing", (None, None, "Unknown command: not_existing")),
        ("not existing", (None, None, "Unknown command: not")),
        ("help", ("help", None, None)),
        ("firmware", ("firmware", None, None)),
        ("bt", (None, None, "Subcommand required: ['on', 'off', 'mac']")),
        ("bt on", ("bt on", None, None)),
        ("bt off", ("bt off", None, None)),
        ("bt mac", ("bt mac", None, None)),
        ("config", (None, None, "Subcommand required: ['get', 'set']")),
        ("config get", ("config get", None, None)),
        ("config set", (None, None, "Subcommand required: ['sensitivity', 'threshold', 'mixed']")),
        ("config set sensitivity", (None, None, "Parameter required: [<class 'int'>, <class 'int'>, <class 'int'>]")),
        ("config set threshold", (None, None, "Parameter required: [<class 'int'>, <class 'int'>, <class 'int'>]")),
        ("config set sensitivity [1,2,3]", ("config set sensitivity", [1, 2, 3], None)),
        ("config set threshold [1,2,3]", ("config set threshold", [1, 2, 3], None)),
        ('config set threshold [1,2,"3"]', (None, None, "Invalid parameter: expected <class 'int'> and position 2 but got <class 'str'> (3)")),
        ("config set threshold [1,2]", (None, None, "Invalid parameter: expected array [<class 'int'>, <class 'int'>, <class 'int'>]")),
        ("config set threshold [1,2,]", (None, None, "Invalid parameter format")),
        ("stringtest", (None, None, "Parameter required: <class 'str'>")),
        ("stringtest foobar", ("stringtest", "foobar", None)),
        ("stringtest foo bar", ("stringtest", "foo", None)),
        ("inttest", (None, None, "Parameter required: <class 'int'>")),
        ("inttest 123456789", ("inttest", 123456789, None)),
        ("inttest 1 2 ", ("inttest", 1, None)),
        ("inttest '12'", (None, None, "Invalid parameter format")),
        ('config set mixed ["aa",2,1.2]', ("config set mixed", ['aa', 2, 1.2], None)),
        ('config set mixed ["aa",2]', (None, None, "Invalid parameter: expected array [<class 'str'>, <class 'int'>, <class 'float'>]")),
        ('config set mixed ["aa"]', (None, None, "Invalid parameter: expected array [<class 'str'>, <class 'int'>, <class 'float'>]")),
        ("floattest 1", ("floattest", 1, None)),
        ("floattest 3.141592653589793", ("floattest", 3.141592653589793, None)),
        ("floattest err", (None, None, "Invalid parameter format"))
    ]

    count = 0
    passed = 0
    for case in cases:
        count += 1
        if check(cp, case[0], case[1]):
            passed += 1

    print(f"Tests done. Count: {count}, Passed: {passed}, Failed: {count - passed}")
