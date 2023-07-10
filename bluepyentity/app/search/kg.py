'''kg queries component'''
import json
import os
from dataclasses import dataclass
from datetime import datetime
import urllib.parse

import requests
from textual import log


@dataclass
class PropertyDefinition:
    # example of a property definition {"property": {"type": "uri", "value": "http://schema.org/name"}, "value": {"type": "literal", "value": "990827IN5HP3"}},
    # we store "http://schema.org/name" and "type":"literal"
    property_type: str
    property_name: str


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


def load_types(org, project, token, log_request_dir=None):
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
    if log_request_dir:
        base_name = datetime.now().strftime("%Y-%m-%d-%H:%M:%S.%f")
        with open(os.path.join(log_request_dir, base_name + ".http"), "w") as f:
            f.write(str(type_url))
    req.raise_for_status()
    response = req.json()

    if log_request_dir:
        with open(os.path.join(log_request_dir, base_name + ".json"), "w") as f:
            json.dump(response, f)
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
        with open(os.path.join(log_request_dir, base_name + ".sparql"), "w") as f:
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
        with open(os.path.join(log_request_dir, base_name + ".json"), "w") as f:
            json.dump(res, f)
    return res


def get_first_entity_of_type(org, project, token, type, log_dir):
    """get the first entity of a given type"""
    request_body = (
        f" SELECT ?id ?mytype\n"
        f"WHERE {{\n"
        f"BIND(<{type}>  as ?mytype) .\n"
        f" ?id <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> ?mytype.\n"
        f"}}\n"
        f"LIMIT 1\n"
    )
    res = perform_sparql_query(org, project, token, request_body, log_dir)
    entity_id = res[0]["id"]["value"]
    return entity_id


def get_properties_of_type(org, project, token, type, log_dir):
    """get the properties of a type using the first instance found"""
    first_entity_id = get_first_entity_of_type(org, project, token, type, log_dir)
    request_body = (
        f"SELECT DISTINCT ?property ?value \n"
        f"WHERE {{\n"
        f"BIND(<{first_entity_id}>  as ?id) .\n"
        f"?id ?property ?value.\n"
        f"}}\n"
        f"LIMIT 60\n"
    )
    l_properties = perform_sparql_query(org, project, token, request_body, log_dir)
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

    select_clause = "SELECT DISTINCT ?id "
    type_clause = (
        "?id <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> " f"<{query_definition.type}>.\n"
    )
    filter_clause = ""
    pred_property_def = query_definition.property_predicate.property_definition
    if pred_property_def:
        filter_clause = (
            f"?id <{pred_property_def.property_name}> ?filterpredicate .\n"
            f"FILTER(CONTAINS(str(?filterpredicate), "
            f'"{query_definition.property_predicate.property_value}")).\n'
        )
    order_clause = ""
    if query_definition.order_by:
        order_predicate = f"?id <{query_definition.order_by.property_name}> ?orderpredicate . \n"
        order_clause = "ORDER BY ?orderpredicate ?id"
    else:
        order_predicate = ""
        order_clause = "ORDER BY ?id"
    request_body = (
        f"{select_clause} \n"
        f"WHERE {{"
        f"{type_clause}"
        f"{filter_clause}"
        f"{order_predicate}"
        f"}}\n"
        f"{order_clause}\n"
        f"limit 5000"
    )
    log(f"request {request_body}")
    return request_body


def retrieve_entities(org, project, token, entity_ids, log_request_dir=None):
    """retrieve a list of entities based on their @id"""
    l_results = []
    # one day that will happen in 1 go
    for entity_id in entity_ids:
        l_results.append(retrieve_entity(org, project, token, entity_id, log_request_dir))
    return l_results


def retrieve_entity(org, project, token, entity_id, log_request_dir=None):
    """retrieve an entity using resource REST API"""
    encoded_id = urllib.parse.quote(entity_id, safe="")
    data_url = f"https://bbp.epfl.ch/nexus/v1/resources/{org}/{project}/_/{encoded_id}"
    req = requests.get(
        data_url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    if log_request_dir:
        base_name = datetime.now().strftime("%Y-%m-%d-%H:%M:%S.%f")
        with open(os.path.join(log_request_dir, base_name + ".http"), "w") as f:
            f.write(str(data_url))
    try:
        response = None
        req.raise_for_status()
        response = req.json()
        if log_request_dir:
            with open(os.path.join(log_request_dir, base_name + ".json"), "w") as f:
                json.dump(response, f)

    except Exception as e:
        if log_request_dir:
            with open(os.path.join(log_request_dir, base_name + ".err"), "w") as f:
                f.write(f"exception type: {str(type(e))} text: {str(e)}")
                if response:
                    f.write(f"response: {str(req.text)}")
        return {}
    return response


def convert_results(results):
    """convert results to be similar to a sparql query result"""
    converted_results = []
    for res in results:
        elem = {}
        for key in res.keys():
            elem[key] = {"type": "dummy", "value": res[key]}
        converted_results.append(elem)
    return converted_results


def format_pg_res(pg_res):
    res = convert_results(pg_res)
    return res


def run_query(org, project, token, query_definition, log_request_dir=None):
    """execute a query_definition"""
    request_body = build_request_body(query_definition)
    res = perform_sparql_query(org, project, token, request_body, log_request_dir)
    entity_ids = [entity["id"]["value"] for entity in res]
    pg_res = retrieve_entities(org, project, token, entity_ids, log_request_dir)
    res = format_pg_res(pg_res)
    log(f"results: {res}")
    return res


def create_property_definitions(input):
    """create a list of PropertyDefinition out of a SPARQL query result"""

    def create_definition_from_item(input_item):
        return PropertyDefinition(
            property_type=input_item["value"].get("type"),
            property_name=input_item["property"].get("value"),
        )

    return [create_definition_from_item(item) for item in input]
