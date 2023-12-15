from langchain.chains.query_constructor.schema import VirtualColumnName
from langchain.chains.query_constructor.base import AttributeInfo

def map_chinese_metadata(name,database='opensearch'):
    if database == 'myscale':
        return VirtualColumnName(name=name, column=f"metadata.`{name}`")
    else:
        return name

def get_metadata_field_info(database):
    metadata_field_info = [
        AttributeInfo(
            name=map_chinese_metadata("城市",database),
            description="酒店所在的城市",
            type="string",
        ),
        AttributeInfo(
            name=map_chinese_metadata("地区",database),
            description="酒店所在的城市区域",
            type="string",
        ),
        AttributeInfo(
            name=map_chinese_metadata("酒店名",database),
            description="酒店的名称",
            type="string",
        ),
        AttributeInfo(
            name=map_chinese_metadata("星级",database),
            description="酒店的星级",
            type="string",
        ),
        AttributeInfo(
            name=map_chinese_metadata("地铁站",database),
            description="酒店所在地附近的地铁站",
            type="string",
        ),    
        AttributeInfo(
            name=map_chinese_metadata("最大容纳人数",database),
            description="酒店中举办活动的会场可以容纳的最大人数",
            type="float",
        ),    
        AttributeInfo(
            name=map_chinese_metadata("会场全天价格",database),
            description="酒店中举办活动的会场的全天价格",
            type="float",
        ),     
        AttributeInfo(
            name=map_chinese_metadata("会场半天价格",database),
            description="酒店中举办各类活动的会场的半天价格",
            type="float",
        )
    ]
    return metadata_field_info
    
def get_document_content_description():
    document_content_description = "对酒店或举办活动场地的描述"
    return document_content_description