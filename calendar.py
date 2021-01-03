import math
import re
import datetime as dt
from pylatex import Document, TikZ, TikZNode, TikZDraw, TikZCoordinate, TikZUserPath, TikZOptions, TikZScope, NewPage

def pairs(a: list):
    if not a:
        raise StopIteration
    i = 1
    while i < len(a):
        yield (a[i - 1], a[i])
        i += 1
    else:
        yield (a[i - 1], a[0])

def ang(i: int, n: int):
    return 2 * math.pi * (i / n)

def point(x, y, r, i, n, rot):
    rot += 90.0
    return (
        round(x + r * math.cos(ang(i, n) + math.radians(rot)), 3),
        round(y + r * math.sin(ang(i, n) + math.radians(rot)), 3)
    )

def shape(x, y, n=3, r=20, rot=0.0):
    return [point(x, y, r, i, n, rot) for i in range(n)]

class Cell:

    def __init__(self, x, y, rot, n, size):
        self.x = x
        self.y = y
        self.rot = rot
        self.n = n
        self.size = size
        self.point_pairs = list(pairs(shape(self.x, self.y, self.n, self.size, self.rot)))

class Calendar:

    DX = .5
    DY = .5

    ROT = 72.

    DAY_DELTA = dt.timedelta(days=1)

    DATE_RE = re.compile(r'([0-3]?[0-9])\/([0-1]?[0-9])')

    MONTH_NAMES = {
        1: 'Janeiro',
        2: 'Fevereiro',
        3: 'Março',
        4: 'Abril',
        5: 'Maio',
        6: 'Junho',
        7: 'Julho',
        8: 'Agosto',
        9: 'Setembro',
        10: 'Outubro',
        11: 'Novembro',
        12: 'Dezembro'
        }

    SIZE = 3.0
    N = 5

    def __init__(self, fname: str = None, debug=False):
        self.year = dt.date.today().year
        self.dates = set()
        if fname is not None:
            with open(fname, 'r') as file:
                for line in file:
                    match = self.DATE_RE.match(line)
                    date = dt.date(self.year, int(match.group(2)), int(match.group(1)))
                    self.dates.add(date)

        self.size = self.SIZE
        self.n = self.N

        self.cell_stack = [Cell(0.0, 0.0, 0.0, self.n, self.size)]

        self.debug = debug

        if self.debug: print(f"NOW:\nx, y = { self.xy }\nrot = { self.rot :.4f}")

    @property
    def cell(self):
        return self.cell_stack[-1]

    @property
    def xy(self):
        return (self.cell.x, self.cell.y)

    @property
    def rot(self):
        return self.cell.rot

    @property
    def point_pairs(self):
        return self.cell.point_pairs

    def draw(self):
        self.page_1 = Document(f'calendar_{self.year}_page1', documentclass='standalone')
        
        first_side = [5, 6, 4, 2, 10]
        with self.page_1.create(TikZ()) as self.pic:
            self.draw_face(1)
            for i, m in enumerate(first_side):
                if self.debug: print(f'ON CELL {m}')
                self.next_cell(i)
                self.draw_face(m)
                self.draw_folds(1, 4)
                self.prev_cell()

        self.page_2 = Document(f'calendar_{self.year}_page2', documentclass='standalone')

        second_side = [3, 11, 9, 7, 8]
        with self.page_2.create(TikZ()) as self.pic:
            self.draw_face(12)
            for i, m in enumerate(second_side):
                if self.debug: print(f'ON CELL {m}')
                self.next_cell(i)
                self.draw_face(m)
                self.draw_folds(1, 4)
                self.prev_cell()

        self.page_1.generate_pdf(f'calendar_{self.year}_page1', clean_tex=True)
        self.page_2.generate_pdf(f'calendar_{self.year}_page2', clean_tex=True)


    def draw_face(self, month: int):
        self.draw_shape()
        self.draw_calendar(month)

    def draw_shape(self):
        for x, y in self.point_pairs:
            self.pic.append(TikZDraw([str(x), '--', str(y)]))

    def draw_folds(self, *i):
        for j in i:
            x, y = self.point_pairs[j]
            z = point(*self.xy, self.size, j + 0.5, self.n, self.rot)
            self.pic.append(TikZDraw([str(x), '--', str(z), '--', str(y)]))
        
    def draw_calendar(self, month: int):
        scope_kwargs = {
            'shift': f'{{({self.x:.4f}, {self.y:.4f})}}',
            'rotate': f'{self.rot:.4f}'
            }
        scope_options = TikZOptions(**scope_kwargs)
        scope = TikZScope(options=scope_options)

        rotation = {'rotate': f'{self.rot:.4f}'}

        if self.debug:
            debug_options = TikZOptions(**rotation)
            scope.append(TikZNode(text=r'\color{red} x', at=TikZCoordinate(0.0, 0.0), options=debug_options))

        ## First, the title
        title_xy = (0.0, 2.5 * self.DY)
        title_coords = TikZCoordinate(*title_xy)
        title_options = TikZOptions(**rotation)
        title_text = f'{{\\bfseries\\color{{blue!50}} {self.MONTH_NAMES[month]}}} {self.year}'
        title_node = TikZNode(text=title_text, at=title_coords, options=title_options)

        scope.append(title_node)

        ## Now the days
        default_options = TikZOptions(align='right', anchor='base', **rotation)
        special_options = TikZOptions(draw='none', radius='0.2', anchor='base', fill='blue!20')
        magical_options = TikZOptions(draw='blue!30', radius='0.2', anchor='base', fill='none')
        
        day = dt.date(self.year, month, 1)
        col = (day.weekday() + 1) % 7
        row = 0 if col != 0 else -1
    
        x0 = -3 * self.DX
        y0 = self.DY
        
        while day.month == month:
            col = (day.weekday() + 1) % 7
            if col == 0:
                color = 'blue!50'
                row += 1
            else:
                color = 'black'

            x = x0 + float(self.DX * col)
            y = y0 - float(self.DY * row)

            if day in self.dates:
                if col == 0:
                    scope.append(TikZDraw([f'({x:.5f}, {y+0.125:.5f})', 'circle'], options=magical_options))
                else:
                    scope.append(TikZDraw([f'({x:.5f}, {y+0.125:.5f})', 'circle'], options=special_options))

            xy = TikZCoordinate(x, y)
        
            node = TikZNode(text=f'\\color{{{color}}} {day.day}', at=xy, options=default_options)
            
            scope.append(node)

            day = day + self.DAY_DELTA

        self.pic.append(scope)

    def next_cell(self, i):
        if self.debug: print(f"BEFORE:\nx, y = { self.xy }\nrot = { self.rot :.4f}")
        
        u, v = self.point_pairs[i]

        if self.debug: print(f"u = {u}\nv = {v}")

        x, y = (u[0] + v[0] - self.x, u[1] + v[1] - self.y)

        rot = (self.rot + 36. + 72. * i) % 360.

        self.cell_stack.append(Cell(x, y, rot, self.n, self.size))

        if self.debug: print(f"NOW:\nx, y = { self.xy }\nrot = { self.rot :.4f}")

    def prev_cell(self):
        self.cell_stack.pop()

    @property
    def x(self):
        return self.xy[0]

    @property
    def y(self):
        return self.xy[1]

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) >= 2:
        fname: str = sys.argv[1]
    else:
        fname: str = None

    calendar = Calendar(fname, debug=False)
    calendar.draw()
