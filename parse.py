import json

# NOTE(skraynev): the original code version was taken from
# https://github.com/asalkeld/convergence-rally/blob/master/parse.py

def parse_file(file_name):

    export = {'heat.create_stack': {},
              'heat.update_stack': {},
              'heat.delete_stack': {}}
    with open(file_name) as fi:
        js = json.load(fi)
        for f in js:
            updated_num = 0
            scen_args = f['key']['kw']['args']
            # if scenario has not any parameters we should set it to 0
            if 'parameters' in scen_args:
                num_instances = scen_args['parameters']['num_instances']
            else:
                num_instances = 0

            if 'updated_parameters' in scen_args:
                updated_num = scen_args['updated_parameters']['num_instances']
            else:
                updated_num = 0

            for res in f['result']:
                results = res['atomic_actions']
                for rn in results:
                    if results[rn] is not None:
                        if rn == 'heat.update_stack':
                            inst_num = updated_num - num_instances
                        elif rn == 'heat.delete_stack':
                            inst_num = max(updated_num, num_instances)
                        else:
                            inst_num = num_instances
                        if inst_num in export[rn]:
                            if not isinstance(export[rn][inst_num], list):
                                export[rn][inst_num] = [
                                    export[rn][inst_num]
                                ]
                            export[rn][inst_num].append(results[rn])
                        else:
                            export[rn][inst_num] = results[rn]

    # calculate average value if we have several execution
    for action in export:
        for inst_num in export[action]:
            if isinstance(export[action][inst_num], list):
                average = (sum(export[action][inst_num]) /
                           len(export[action][inst_num]))
                export[action][inst_num] = average


    return export

