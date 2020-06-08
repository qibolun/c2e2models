from lxml import etree
import argparse
import re
# def prettify(elem):
#     """Return a pretty-printed XML string for the Element.
#     """
#     rough_string = ET.tostring(elem, 'utf-8')
#     reparsed = minidom.parseString(rough_string)
#     return reparsed.toprettyxml(indent="    ")

def main(xml_fn,cfg_fn,output_fn):
    hyxml = etree.Element('hyxml')
    hyxml.set('type',"Model")
    
    initial_mode = ""
    if xml_fn!=None:
        print("Parse spaceex xml file")
        automaton = etree.SubElement(hyxml,'automaton')
        automaton.set('name','default_automaton')
        p = etree.XMLParser(huge_tree=True)
        spaceex_xml_tree = etree.parse(xml_fn,parser=p)
        spaceex_xml_root = spaceex_xml_tree.getroot()
        component = spaceex_xml_root[0]
        tmp = None
        ns = component.nsmap
        ns = ns[tmp]

        const_list = []
        for param in component.findall("{"+ns+"}"+'param'):
            variable = etree.SubElement(automaton,'variable')
            name = param.get('name')
            variable.set('name',name)
            variable.set('type','real')
            variable.set('scope','LOCAL_DATA')
            if param.get('dynamics') == 'const':
                const_list.append(name)

        mode_id = str(int(1))

        print("  Convert spaceex mode to C2E2 format")
        for location in component.findall("{"+ns+"}"+'location'):
            mode = etree.SubElement(automaton,'mode')
            mode_id = location.get('id')
            # mode_id = param.get('id')
            mode.set('id',mode_id)
            name = location.get('name')
            mode.set('name',name)
            if mode_id == '1':
                mode.set('initial','True')
                initial_mode = name
            else:
                mode.set('initial','False')
            print("    Convert flow for mode "+name)
            for flow in location.findall("{"+ns+"}"+'flow'):
                eqns = flow.text
                eqns = eqns.replace('\n','')
                eqns = eqns.replace(' ','')
                eqns = eqns.replace("'",'_dot')
                eqns = eqns.replace("==",'=')
                eqns = eqns.split('&')
                for eqn in eqns:
                    dai = etree.SubElement(mode,'dai')
                    dai.set('equation',eqn)
            for variable in const_list:
                dai = etree.SubElement(mode,'dai')
                dai.set('equation',variable+"_dot=0")


            print("    Convert invariants for mode "+name)            
            for inv in location.findall("{"+ns+"}"+'invariant'):
                if inv.text!=None:
                    eqns = inv.text
                    eqns = eqns.replace('\n','')
                    eqns = eqns.replace(' ','')
                    eqns = eqns.replace('&','&&')
                    invariant = etree.SubElement(mode,'invariant')
                    invariant.set('equation', eqns)
        
        transition_id = int(0)
        print("Convert Spaceex Transition to C2E2 format")
        for transition_sx in component.findall("{"+ns+"}"+'transition'):
            transition = etree.SubElement(automaton,'transition')
            transition.set('id',str(transition_id))
            transition_id += int(1)
            source = transition_sx.get('source')
            transition.set('source',source)
            dest = transition_sx.get('target')
            transition.set('destination',dest)
            # convert guard equations
            for guard_sx in transition_sx.findall("{"+ns+"}"+"guard"):
                guard_eqn = guard_sx.text
                guard = etree.SubElement(transition,'guard')
                guard.set('equation',guard_eqn)

            # TODO: convert action equations      

        composition = etree.SubElement(hyxml,'composition')
        composition.set('automata','default_automaton')

    if cfg_fn!=None:
        print("Parse spaceex cfg file")
        time_horizon = ''
        initial_set = ""
        property_name = ""
        with open(cfg_fn,'r') as cfg_file:
            for line in cfg_file:
                # if line.startswith('scenario'):
                #     val = re.search('"(.+?)"',line).group(1)
                #     val = val.replace(' ','')
                    # property_name = val
                if line.startswith('time-horizon'):
                    _,val = line.strip().split('=')
                    val = val.replace(' ','')
                    time_horizon = val
                if line.startswith('initially'):
                    val = re.search('"(.+?)"',line).group(1)
                    initial_set = val
                    initial_set = initial_set.replace("&","&&")
                    initial_set = initial_set.replace(' ','')
        prop = etree.SubElement(hyxml,'property')
        initial_eqns = ""
        initial_set = initial_set.split("&&")
        for eqns in initial_set:
            if eqns.count("<=")>1 or eqns.count(">=")>1:
                if "<=" in eqns:
                    eqns = eqns.split("<=")
                    initial_eqns = initial_eqns+eqns[1]+">="+eqns[0]+"&&"+eqns[1]+"<="+eqns[2]+"&&"
                elif ">=" in eqns:
                    eqns = eqns.split(">=")
                    initial_eqns = initial_eqns+eqns[1]+"<="+eqns[0]+"&&"+eqns[1]+">="+eqns[2]+"&&"
            else:
                initial_eqns = initial_eqns+eqns+"&&"
        initial_eqns = initial_eqns.strip("&")
        init_eqns = initial_mode+":"+initial_eqns
        prop.set('initialSet',init_eqns)
        prop.set('name',property_name)
        prop.set('type','Safety')
        prop.set('unsafeSet','')

        parameters = etree.SubElement(prop,'parameters')
        parameters.set('kvalue','1000')
        parameters.set('timehorizon',time_horizon)
        parameters.set('timestep','0.1')


    res = etree.tostring(hyxml,encoding="UTF-8",xml_declaration=True,pretty_print=True,doctype='<!DOCTYPE hyxml>')
    with open(output_fn,'wb+') as file:
        file.write(res)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = 'Convert SpaceEX model to C2E2 model')

    xml_fn_default = None
    cfg_fn_default = None
    output_fn_default = None

    parser.add_argument('--xml',type = str, help = 'xml file name for SpaceEX model',default = xml_fn_default)
    parser.add_argument('--cfg',type = str, help = 'cfg file name for SpaceEX model',default = cfg_fn_default)
    parser.add_argument('--output',type = str, help = 'output file name for C2E2 model',default = output_fn_default)

    argv = parser.parse_args()

    xml_fn = argv.xml
    cfg_fn = argv.cfg
    output_fn = argv.output

    if output_fn == None:
        sys.exit('please provide output model file name')
    
    main(xml_fn,cfg_fn,output_fn)

