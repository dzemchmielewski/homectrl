class Colors:

    def __init__(self, colors: list[int]):
        self.colors = colors
        self.background = self.get(0)
        self.foreground = self.get(100)
        if not len(self.colors) in [2, 4]:
            raise Exception(f'Scale length = {len(self.colors)} not supported')
        if len(self.colors) >= 2:
            self.WHITE = self.get(0)
            self.BLACK = self.get(100)
        if len(self.colors) == 4:
            self.LIGHT = self.get(30)
            self.DARK = self.get(60)

        self.map = {
            'text': self.get(100),
            'background': self.get(0),
            'foreground': self.get(100),
            'light': self.get(30) if len(self.colors) == 4 else self.get(0),
            'dark': self.get(60) if len(self.colors) == 4 else self.get(100),
        }

    def get(self, percent_or_key: float | str) -> int:
        if isinstance(percent_or_key, str):
            return self.map[percent_or_key]
        elif isinstance(percent_or_key, int) or isinstance(percent_or_key, float):
            index = int((len(self.colors) - 1) * (100 - percent_or_key) / 100)
            return self.colors[index]
        else:
            raise Exception(f'Unsupported argument type: {type(percent_or_key)}')


if __name__ == '__main__':

    def test(colors: Colors):
        print(f"Testing scale: {colors.__class__.__name__}")
        for p in range(0, 101, 1):
            color = colors.get(p)
            print(f"  Percent: {p:3}% -> Color: {color}")
        print(f"  Background: {colors.background}, Foreground: {colors.foreground}")
        print(f"WHITE: {colors.WHITE}, LIGHT: {colors.LIGHT}, DARK: {colors.DARK}, BLACK: {colors.BLACK}")

    test(Colors([0, 1, 2, 3]))  # 4-level scale

