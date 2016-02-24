#!/usr/bin/python

import argparse
import json
from os import listdir
from os import path
from parse import parse_file
import plotly
from plotly.graph_objs import Scatter, Layout
import random

parser = argparse.ArgumentParser()
parser.add_argument("res_path_conv", help="path to directory with test results")
parser.add_argument("res_path_def", help="path to directory with test results")
parser.add_argument("output_name", help="name of output 'html' file with plot")
args = parser.parse_args()

def add_key_if_need(data, key, axis=False):
    if key not in data:
        if axis:
            data.update({key: {'x': [], 'y': []}})
        else:
            data.update({key: {}})

    return data[key]

def group_and_parse_files_by_scenario(dir_path):
    files = [f for f in listdir(dir_path)
             if (path.isfile('/'.join([dir_path, f])) and
                 f.endswith('.json'))]
    scenarios = {}
    for f in files:
        # scenario name should be in format: <sceanrio-name>-<count>.json
        name = f.split('-')[0]
        count = f.split('-')[1].split('.')[0]
        content = parse_file('/'.join([dir_path, f]))
        s_data = add_key_if_need(scenarios, name)
        for action in content:
            s_action = add_key_if_need(s_data, action)
            s_count = add_key_if_need(s_action, count)
            s_count.update(content[action])

    return scenarios

# Data stored format is:
# full_data -> scenario_name -> action -> scenario-count(engine_num) ->
#    ->  res_num -> time of action

# do it per action
# the format is: eng_num: {x: [res_num], y: [time]}
# or: res_num: {x: [eng_num], y: [time]}
def get_x_y_data(action_data, fixed='eng_num'):
    # fixed can be equals 'eng_num' or 'res_num'
    whole_data = {}
    if fixed == 'eng_num':
        for eng_num in action_data:
            res = add_key_if_need(whole_data, float(eng_num), axis=True)
            for res_num in action_data[eng_num]:
                res['x'].append(res_num)
                res['y'].append(action_data[eng_num][res_num])
    elif fixed == 'res_num':
        for eng_num in action_data:
            for res_num in action_data[eng_num]:
                res = add_key_if_need(whole_data, res_num, axis=True)
                res['x'].append(float(eng_num))
                res['y'].append(action_data[eng_num][res_num])

    # sort x/y pairs by x
    for pairs in whole_data.itervalues():
        (x , y) = zip(*sorted(zip(pairs['x'], pairs['y']),
                              key=lambda pair: pair[0]))
        pairs['x'] = list(x)
        pairs['y'] = list(y)


    return whole_data

def build_trace(pairs, action):
    colors = {
        'r': random.randrange(0, 255),
        'g': random.randrange(0, 255),
        'b': random.randrange(0, 255)
    }
    trace = Scatter(
        x = pairs['x'],
        y = pairs['y'],
        name = action,
        line = dict(
            color = ('rgb(%(r)s, %(g)s, %(b)s)' % colors),
            width = 4
        )
    )
    return trace


def draw_graphs_by_groups(traces, action, scenario, fixed='eng_num'):
    title = ('Comparison default and convergence engines for <%s> with '
             'scenario (%s)' % (action, scenario))

    if fixed == 'eng_num':
        x_title = 'Resources invovment in action'
    elif fixed == 'res_num':
        x_title = 'Heat Engines'

    layout = dict(title = title,
                  xaxis = dict(title = 'Num of %s' % x_title),
                  yaxis = dict(title = 'Average time for operation'),
                 )
    fig = dict(data=traces, layout=layout)

    filename = '-'.join([action, scenario])
    if not filename.endswith('html'):
        filename = '.'.join([filename, 'html'])
    # offline
    plotly.offline.plot(fig, filename=filename)
    # online
    #plotly.iplot(fig, filename='styled-line')


def main():
    data_conv = group_and_parse_files_by_scenario(args.res_path_conv)
    data_def = group_and_parse_files_by_scenario(args.res_path_def)
    # we need to remove this data, because this sceanrio does
    # only create and delete, so data for update is empty
    data_conv['nested_test_resource.yaml'].pop('heat.update_stack')
    data_def['nested_test_resource.yaml'].pop('heat.update_stack')

    if data_conv.keys() != data_def.keys():
        raise ValueError('Scenarios should be eqal for both directories')

    for scenario in data_conv:
        for action in data_conv[scenario]:
            # we have different executions with different numbers of resources
            # only for this scenario
            if scenario == 'increasing_resources.yaml':
                xy_conv = get_x_y_data(data_conv[scenario][action])
                xy_def = get_x_y_data(data_def[scenario][action])
            else:
                xy_conv = get_x_y_data(data_conv[scenario][action],
                                       fixed='res_num')
                xy_def = get_x_y_data(data_def[scenario][action],
                                      fixed='res_num')
            traces_conv = []
            for eng_num, pairs in xy_conv.iteritems():
                trace_name = '='.join(['conv_eng_works', str(eng_num)])
                traces_conv.append(build_trace(pairs, trace_name))
            traces_def = []
            for eng_num, pairs in xy_def.iteritems():
                trace_name = '='.join(['def_eng_works', str(eng_num)])
                traces_def.append(build_trace(pairs, trace_name))
            draw_graphs_by_groups(traces_conv+traces_def, action, scenario)

#        traces = build_traces(data)

main()
