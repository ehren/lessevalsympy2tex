import ast

import sympy
import asttokens


# Python to latex converter using Sympy's latex printing for most mathematical
# functions but avoids the term reordering (and perhaps a few evaluations) 
# incurred working with fully "sympified" sympy expressions (even those 
# created with the evaluate=False keyword). Based on Geoff Reedy's program at 
# https://stackoverflow.com/a/3874621/1391250


class LatexVisitor(ast.NodeVisitor):

    def __init__(self, atok):
        super().__init__()
        self._atok = atok

    def prec(self, n):
        return getattr(self, 'prec_'+n.__class__.__name__, getattr(self, 'generic_prec'))(n)

    def visit_Call(self, n):
        func = self.visit(n.func)

        # Ad-hoc handling of a few functions (differently than Sympy's defaults):

        if func == 'Sum' or func == 'Product':
            body_node = n.args[0]
            body_source = self._atok.get_text(body_node)
            body = self.visit(body_node)
            needs_parentheses = sympy.sympify(body_source).is_Add
            if needs_parentheses:
                body = r"\left({}\right)".format(body)
            index, lower_limit, upper_limit = map(self.visit, n.args[1].elts)
            sum_or_prod = 'sum_' if func == 'Sum' else 'prod_'
            return r'\%s {%s=%s}^{%s} %s' % (sum_or_prod, index, lower_limit, upper_limit, body)

        if func in ("fibonacci", "lucas"):
            args = ', '.join(map(self.visit, n.args))

            if func == 'fibonacci':
                return 'F_{%s}' % args
            elif func == 'lucas':
                return 'L_{%s}' % args

        # Generic building of a sympify compatible python string but with all 
        # subexpressions replaced by dummy symbolic vars to prevent eager 
        # evaluation of their structure by Sympy (while separately creating 
        # latex for the subexpressions with our own mechanism):

        dummified_args = []
        replacements = {}

        for arg in n.args:
            arg_text = self._atok.get_text(arg)
            sympified_arg = sympy.sympify(arg_text)
            if isinstance(sympified_arg, sympy.Expr):
                dummy_arg = "py2texdummyvar{}".format(len(dummified_args))
                our_latex_arg = self.visit(arg)
                replacements[dummy_arg] = our_latex_arg
                dummified_args.append(dummy_arg)
            else:
                # non Expr argument e.g. a tuple
                # let sympy handle latex generation (don't visit / don't replace arg with dummy)
                dummified_args.append(str(sympified_arg))

        # Get Sympy's latex for the outer dummified expression:

        func_text = self._atok.get_text(n.func)
        s = "%s(%s)" % (func_text, ",".join(dummified_args))
        sympified_dummy_expr = sympy.sympify(s)
        sympy_latex = sympy.latex(sympified_dummy_expr)

        # Replace dummy expressions with our separately generated latex:

        our_latex = sympy_latex
        for dummy in replacements.keys():
            our_latex = our_latex.replace(dummy, replacements[dummy])

        return our_latex

    def prec_Call(self, n):
        return 1000

    def visit_Name(self, n):
        return n.id

    def prec_Name(self, n):
        return 1000

    def visit_UnaryOp(self, n):
        if self.prec(n.op) > self.prec(n.operand):
            return r'%s \left(%s\right)' % (self.visit(n.op), self.visit(n.operand))
        else:
            return r'%s %s' % (self.visit(n.op), self.visit(n.operand))

    def prec_UnaryOp(self, n):
        return self.prec(n.op)

    def visit_BinOp(self, n):
        if self.prec(n.op) > self.prec(n.left):
            left = r'\left(%s\right)' % self.visit(n.left)
        else:
            left = self.visit(n.left)
        if self.prec(n.op) > self.prec(n.right) or (  # fix for "3-(1+2)" by Edoot Nov 24 '15:
                isinstance(n.op, ast.Sub) and self.prec(n.op) == self.prec(n.right)):
            right = r'\left(%s\right)' % self.visit(n.right)
        else:
            right = self.visit(n.right)
        if isinstance(n.op, ast.Div):
            return r'\frac{%s}{%s}' % (self.visit(n.left), self.visit(n.right))
        elif isinstance(n.op, ast.FloorDiv):
            return r'\left\lfloor\frac{%s}{%s}\right\rfloor' % (self.visit(n.left), self.visit(n.right))
        elif isinstance(n.op, ast.Pow):
            return r'(%s)^{%s}' % (left, self.visit(n.right))
        # elif isinstance(n.op, ast.Mult):
        #     return r'%s%s%s' % (left, self.visit(n.op), right)
        else:
            return r'%s%s%s' % (left, self.visit(n.op), right)

    def prec_BinOp(self, n):
        return self.prec(n.op)

    def visit_Sub(self, n):
        return '-'

    def prec_Sub(self, n):
        return 300

    def visit_Add(self, n):
        return '+'

    def prec_Add(self, n):
        return 300

    def visit_Mult(self, n):
        return ' '
        # return ''
        #return '\\;'

    def prec_Mult(self, n):
        return 400

    def visit_Mod(self, n):
        return '\\bmod'

    def prec_Mod(self, n):
        return 500

    def prec_Pow(self, n):
        return 700

    def prec_Div(self, n):
        return 400

    def prec_FloorDiv(self, n):
        return 400

    def visit_LShift(self, n):
        return '\\operatorname{shiftLeft}'

    def visit_RShift(self, n):
        return '\\operatorname{shiftRight}'

    def visit_BitOr(self, n):
        return '\\operatorname{or}'

    def visit_BitXor(self, n):
        return '\\operatorname{xor}'

    def visit_BitAnd(self, n):
        return '\\operatorname{and}'

    def visit_Invert(self, n):
        return '\\operatorname{invert}'

    def prec_Invert(self, n):
        return 800

    def visit_Not(self, n):
        return '\\neg'

    def prec_Not(self, n):
        return 800

    def visit_UAdd(self, n):
        return '+'

    def prec_UAdd(self, n):
        return 800

    def visit_USub(self, n):
        return '-'

    def prec_USub(self, n):
        return 800

    def visit_Num(self, n):
        return str(n.n)

    def prec_Num(self, n):
        return 1000

    def generic_prec(self, n):
        return 0


def py2tex(expr):
    # pt = ast.parse(expr)
    # return LatexVisitor().visit(pt.body[0].value)
    atok = asttokens.ASTTokens(expr, parse=True)
    s = LatexVisitor(atok).visit(atok.tree.body[0].value)
    s = s.replace(r"(\left(", r"\left(")
    s = s.replace(r"\right))", r"\right)")
    return s


if __name__ == "__main__":
    print(py2tex("Matrix([[1,fibonacci(n),3],[1,2,3]])"))
    print(py2tex("3-(1+2)/5"))
    print(py2tex("(y*x)"))
    print(py2tex("Piecewise((2, x < 0), (3, True))"))
    print(py2tex("Derivative(x,x)"))
    print(py2tex("1 - Sum(1/5*binomial(k, i)*fibonacci(n+i)**8, (i, 1, k)) + 1"))
    print(py2tex("sqrt(5)"))
    print(py2tex("Sum(i+k, (i, 1, k))"))
    print(py2tex("Sum(i*k, (i, 1, k))"))
    print(py2tex("Sum(k*i, (i, 1, k))"))
    print(py2tex("Integral(1+x-1, (x, 0, oo))"))
    print(py2tex("(Sum((-1)**(i*(n + k + 1))*binomial(p, i)*fibonacci((p/2 - i)*(k + 1))*lucas((p/2 - i)*(2*n + k))/fibonacci(p/2 - i), (i, 0, p/2-1)) + binomial(p, p/2)*(k+1))/5**(p/2)"))
