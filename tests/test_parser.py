from phply.phpparse import parser
from phply.phpast import *
import nose.tools

def eq_ast(input, expected):
    output = parser.parse(input)
    print output
    assert len(output) == len(expected)
    for out, exp in zip(output, expected):
        print out, exp
        nose.tools.eq_(out, exp)

def test_inline_html():
    input = 'html <?php // php ?> more html'
    expected = [InlineHTML('html '), InlineHTML(' more html')]
    eq_ast(input, expected)

def test_echo():
    input = '<?php echo "hello, world!"; ?>'
    expected = [Echo(["hello, world!"])]
    eq_ast(input, expected)

def test_exit():
    input = '<?php exit; exit(); exit(123); die; die(); die(456); ?>'
    expected = [
        Exit(None), Exit(None), Exit(123),
        Exit(None), Exit(None), Exit(456),
    ]
    eq_ast(input, expected)

def test_namespace_names():
    input = r"""<?php
        foo;
        bar\baz;
        one\too\tree;
    ?>"""
    expected = [
        Constant(r'foo'),
        Constant(r'bar\baz'),
        Constant(r'one\too\tree'),
    ]
    eq_ast(input, expected)

def test_unary_ops():
    input = r"""<?
        $a = -5;
        $b = +6;
        $c = !$d;
        $e = ~$f;
    ?>"""
    expected = [
        Assignment(Variable('$a'), UnaryOp('-', 5), False),
        Assignment(Variable('$b'), UnaryOp('+', 6), False),
        Assignment(Variable('$c'), UnaryOp('!', Variable('$d')), False),
        Assignment(Variable('$e'), UnaryOp('~', Variable('$f')), False),
    ]
    eq_ast(input, expected)

def test_assignment_ops():
    input = r"""<?
        $a += 5;
        $b -= 6;
        $c .= $d;
        $e ^= $f;
    ?>"""
    expected = [
        AssignOp('+=', Variable('$a'), 5),
        AssignOp('-=', Variable('$b'), 6),
        AssignOp('.=', Variable('$c'), Variable('$d')),
        AssignOp('^=', Variable('$e'), Variable('$f')),
    ]
    eq_ast(input, expected)

def test_string_offset_lookups():
    input = r"""<?
        "$array[offset]";
        "$array[$variable]";
        "$too[many][offsets]";
        "$next[to]$array";
        "$object->property";
        "$too->many->properties";
        "$adjacent->object$lookup";
        "$two->$variables";
        "stray -> [ ]";
        "not[array]";
        "non->object";
    ?>"""
    expected = [
        ArrayOffset('$array', 'offset'),
        ArrayOffset('$array', Variable('$variable')),
        BinaryOp('.', ArrayOffset('$too', 'many'), '[offsets]'),
        BinaryOp('.', ArrayOffset('$next', 'to'), Variable('$array')),
        ObjectProperty('$object', 'property'),
        BinaryOp('.', ObjectProperty('$too', 'many'), '->properties'),
        BinaryOp('.', ObjectProperty('$adjacent', 'object'), Variable('$lookup')),
        BinaryOp('.', BinaryOp('.', Variable('$two'), '->'), Variable('$variables')),
        'stray -> [ ]',
        'not[array]',
        'non->object',
    ]
    eq_ast(input, expected)

def test_string_curly_dollar_expressions():
    input = r"""<?
        "a${dollar_curly}b";
        "c{$curly_dollar}d";
        "e${$dollar_curly_dollar}f";
        "{$array[0][1]}";
        "{$array['two'][3]}";
        "{$object->items[4]->five}";
        "{${$nasty}}";
        "{${funcall()}}";
        "{${$object->method()}}";
        "{$object->$variable}";
        "{$object->$variable[1]}";
        // "{${static_class::variable}}";
        // "{${static_class::$variable}}";
    ?>"""
    expected = [
        BinaryOp('.', BinaryOp('.', 'a', Variable('$dollar_curly')), 'b'),
        BinaryOp('.', BinaryOp('.', 'c', Variable('$curly_dollar')), 'd'),
        BinaryOp('.', BinaryOp('.', 'e', Variable('$dollar_curly_dollar')), 'f'),
        ArrayOffset(ArrayOffset(Variable('$array'), 0), 1),
        ArrayOffset(ArrayOffset(Variable('$array'), 'two'), 3),
        ObjectProperty(ArrayOffset(ObjectProperty(Variable('$object'), 'items'), 4), 'five'),
        Variable(Variable('$nasty')),
        Variable(FunctionCall('funcall', [])),
        Variable(MethodCall(Variable('$object'), 'method', [])),
        ObjectProperty(Variable('$object'), Variable('$variable')),
        ObjectProperty(Variable('$object'), ArrayOffset(Variable('$variable'), 1)),
        # StaticProperty('static_class', 'variable'),
        # StaticProperty('static_class', Variable('$variable')),
    ]
    eq_ast(input, expected)

def test_function_calls():
    input = r"""<?
        f();
        doit($arg1, &$arg2, 3 + 4);
    ?>"""
    expected = [
        FunctionCall('f', []),
        FunctionCall('doit',
                     [Parameter(Variable('$arg1'), False),
                      Parameter(Variable('$arg2'), True),
                      Parameter(BinaryOp('+', 3, 4), False)]),
    ]
    eq_ast(input, expected)                   

def test_method_calls():
    input = r"""<?
        $obj->meth($a, &$b, $c . $d);
        $chain->one($x)->two(&$y);
    ?>"""
    expected = [
        MethodCall(Variable('$obj'), 'meth',
                   [Parameter(Variable('$a'), False),
                    Parameter(Variable('$b'), True),
                    Parameter(BinaryOp('.', Variable('$c'), Variable('$d')), False)]),
        MethodCall(MethodCall(Variable('$chain'),
                              'one', [Parameter(Variable('$x'), False)]),
                   'two', [Parameter(Variable('$y'), True)]),
    ]
    eq_ast(input, expected)                   

def test_foreach():
    input = r"""<?
        foreach ($foo as $bar) {
            echo $bar;
        }
        foreach ($spam as $ham => $eggs) {
            echo "$ham: $eggs";
        }
        foreach (complex($expression) as &$ref)
            $ref++;
        foreach ($what as &$de => &$dealy):
            yo();
            yo();
        endforeach;
    ?>"""
    expected = [
        ForEach(Variable('$foo'), None, ForEachVariable('$bar', False),
                Block([Echo([Variable('$bar')])])),
        ForEach(Variable('$spam'),
                ForEachVariable('$ham', False),
                ForEachVariable('$eggs', False),
                Block([Echo([BinaryOp('.',
                                      BinaryOp('.', Variable('$ham'), ': '),
                                      Variable('$eggs'))])])),
        ForEach(FunctionCall('complex', [Parameter(Variable('$expression'),
                                                   False)]),
                None, ForEachVariable('$ref', True),
                PostIncDecOp('++', Variable('$ref'))),
        ForEach(Variable('$what'),
                ForEachVariable('$de', True),
                ForEachVariable('$dealy', True),
                Block([FunctionCall('yo', []),
                       FunctionCall('yo', [])])),
    ]
    eq_ast(input, expected)

def test_global_variables():
    input = r"""<?
        global $foo, $bar;
        global $$yo;
        global ${$dawg};
        global ${$obj->prop};
    ?>"""
    expected = [
        Global([Variable('$foo'), Variable('$bar')]),
        Global([Variable(Variable('$yo'))]),
        Global([Variable(Variable('$dawg'))]),
        Global([Variable(ObjectProperty(Variable('$obj'), 'prop'))]),
    ]
    eq_ast(input, expected)

def test_variable_variables():
    input = r"""<?
        $$a = $$b;
        $$a =& $$b;
        ${$a} = ${$b};
        ${$a} =& ${$b};
        $$a->b;
        $$$triple;
    ?>"""
    expected = [
        Assignment(Variable(Variable('$a')), Variable(Variable('$b')), False),
        Assignment(Variable(Variable('$a')), Variable(Variable('$b')), True),
        Assignment(Variable(Variable('$a')), Variable(Variable('$b')), False),
        Assignment(Variable(Variable('$a')), Variable(Variable('$b')), True),
        ObjectProperty(Variable(Variable('$a')), 'b'),
        Variable(Variable(Variable('$triple'))),
    ]
    eq_ast(input, expected)
