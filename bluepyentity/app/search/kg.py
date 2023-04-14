import json
import os
from dataclasses import dataclass
from datetime import datetime

import requests
from textual import log


@dataclass
class ValueDefinition:
    type: str
    datatype: str


@dataclass
class PropertyDefinition:
    value_definition: ValueDefinition
    # something like 'uri'
    type: str
    # something like https://bluebrain.github.io/nexus/vocabulary/constrainedBy
    value: str


@dataclass
class PropertyPredicate:
    property_definition: PropertyDefinition
    property_value: str
    predicate: str


@dataclass
class QueryDefinition:
    # with the namespace
    type: str
    property_predicate: PropertyPredicate
    order_by: PropertyDefinition
    select_clause: list[PropertyDefinition]


def load_types(org, project, token):
    """load all known types using default ES index"""
    type_url = (
        f"https://bbp.epfl.ch/nexus/v1/views/{org}/{project}/"
        "https%3A%2F%2Fbluebrain.github.io%2Fnexus%2Fvocabulary%2FdefaultElasticSearchIndex/_search"
    )
    data = (
        '{"aggregations":{"types":{"filter":{"term":{"_deprecated":false}},'
        '"aggregations":{"filteredByDeprecation":{"terms":{"field":"@type","size":10000}}}}}}'
    )
    req = requests.post(
        type_url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        data=data,
    )
    req.raise_for_status()
    response = req.json()
    type_counts = response["aggregations"]["types"]["filteredByDeprecation"]["buckets"]

    return type_counts


def perform_sparql_query(org, project, token, request_body, log_request_dir=None):
    """perform the SPARQL request from request_body"""
    req_url = (
        f"https://bbp.epfl.ch/nexus/v1/views/{org}/{project}/"
        "https%3A%2F%2Fbluebrain.github.io%2Fnexus%2Fvocabulary%2FdefaultSparqlIndex/sparql"
    )

    if log_request_dir:
        base_name = datetime.now().strftime("%Y-%m-%d-%H:%M:%S.%f")
        with open(os.path.join(log_request_dir, base_name + ".sparql"), 'w') as f:
            f.write(request_body)
    req = requests.post(
        req_url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/sparql-query",
        },
        data=request_body,
    )
    req.raise_for_status()
    res = req.json()["results"]["bindings"]
    if log_request_dir:
        with open(os.path.join(log_request_dir, base_name + ".json"), 'w') as f:
            json.dump(res, f)
    return res


def get_first_entity_of_type(org, project, token, type):
    """get the first entity of a given type"""
    request_body = (
        f" SELECT ?entityid ?mytype\n"
        f"WHERE {{\n"
        f"BIND(<{type}>  as ?mytype) .\n"
        f" ?entityid <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> ?mytype.\n"
        f"}}\n"
        f"LIMIT 1\n"
    )
    res = perform_sparql_query(org, project, token, request_body, "out")
    entity_id = res[0]["entityid"]["value"]
    return entity_id


def get_properties_of_type(org, project, token, type):
    """get the properties of a type using the first instance found"""
    first_entity_id = get_first_entity_of_type(org, project, token, type)
    request_body = (
        f"SELECT DISTINCT ?property ?value \n"
        f"WHERE {{\n"
        f"BIND(<{first_entity_id}>  as ?entityid) .\n"
        f"?entityid ?property ?value.\n"
        f"}}\n"
        f"LIMIT 60\n"
    )
    l_properties = perform_sparql_query(org, project, token, request_body, "out")
    # example {'property': {'type': 'uri',
    #                      'value': 'https://bluebrain.github.io/nexus/vocabulary/constrainedBy'},
    # 'value': {'type': 'uri',
    #          'value': 'https://bluebrain.github.io/nexus/schemas/unconstrained.json'}}

    def get_unique_properties(l_properties):
        ret = []
        types = set()
        for item in l_properties:
            type = item["property"]["value"]
            if type not in types:
                ret.append(item)
                types.add(type)
        return ret

    l_properties = get_unique_properties(l_properties)
    l_properties.append(
        {"property": {"type": "uri", "value": "entityid"}, "value": {"type": "uri", "value": ""}}
    )

    def is_blacklist(property):
        L_BLACKLIST = ["incoming", "outgoing"]

        for b in L_BLACKLIST:
            if b in property["value"]:
                return True
        return False

    filtered_l_properties = [prop for prop in l_properties if not is_blacklist(prop["value"])]
    log(f"number of properties found {len(filtered_l_properties)}")
    return create_property_definitions(filtered_l_properties)


def build_request_body(query_definition):
    """build a SPARQL request from a query definition"""

    def get_property_clause(property_definition: PropertyDefinition, output_name):
        return f"OPTIONAL {{ ?entityid <{property_definition.value}> ?{output_name} . }}\n"

    select_clause = "SELECT DISTINCT ?entityid "
    property_clauses = ""
    map_property_binding = {}
    for idx, property_definition in enumerate(query_definition.select_clause):
        if property_definition.value == "entityid":
            map_property_binding["entityid"] = "entityid"
            continue
        binding = f"o{idx}"
        property_clause = get_property_clause(property_definition, binding)
        map_property_binding[property_definition.value] = binding
        property_clauses += property_clause
        select_clause += "?" + binding + " "

    type_clause = (
        "?entityid <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> "
        f"<{query_definition.type}>.\n"
    )
    filter_clause = ""
    pred_property_def = query_definition.property_predicate.property_definition
    if pred_property_def:
        filter_clause = (
            f"FILTER(CONTAINS(str(?{map_property_binding[pred_property_def.value]}), "
            f'"{query_definition.property_predicate.property_value}")).\n'
        )
    order_clause = ""
    if query_definition.order_by:
        order_clause = f"ORDER BY DESC(?{map_property_binding[query_definition.order_by.value]}), ?entityid"
    else:
        order_clause = f"ORDER BY ?entityid"
    request_body = (
        f"{select_clause} \n"
        f"WHERE {{"
        f"{property_clauses}"
        f"{type_clause}"
        f"{filter_clause}"
        f"}}\n"
        f"{order_clause}\n"
        f"limit 5000"
    )
    log(f"request {request_body}")
    return request_body, map_property_binding


def merge_multivaluated_properties(results):
    """merge property values showing up multiple time into a single list per property"""
    grouped_results = []
    dict_result = {}

    for item in results:
        # assuming id is bound to entityid
        value_id = item["entityid"]["value"]
        ref_item = dict_result.get(value_id, None)
        if not ref_item:
            dict_result[value_id] = item
            grouped_results.append(item)
            continue
        # it is a merge !
        for k, v in item.items():
            ref_data = ref_item.get(k, None)
            if ref_data is None:
                ref_item[k] = v
                continue
            ref_data_value = ref_data["value"]
            if type(ref_data_value) == list:
                new_set = set(ref_data_value)
                new_set.add(v["value"])
                ref_data["value"] = list(new_set)
                continue
            if ref_data_value == v["value"]:
                continue
            else:
                ref_data["value"] = [ref_data_value, v["value"]]
    return grouped_results


def run_query(org, project, token, query_definition, log_request_dir=None):
    request_body, binding = build_request_body(query_definition)
    res = perform_sparql_query(org, project, token, request_body, log_request_dir)
    log(f"number of results from the raw query {len(res)}")
    res = merge_multivaluated_properties(res)
    return res, binding


def create_property_definitions(input):
    """create a list of PropertyDefinition out of a SPARQL query result"""

    def create_definition_from_item(input_item):
        return PropertyDefinition(
            value_definition=ValueDefinition(
                type=input_item["value"].get("type", None),
                datatype=input_item["value"].get("datatype", None),
            ),
            type=input_item["property"].get("type"),
            value=input_item["property"].get("value"),
        )

    return [create_definition_from_item(item) for item in input]
