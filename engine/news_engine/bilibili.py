import json
import time
from bilibili_api import search, sync, video, video_zone
from engine.utils.data.database import get_database, weight_map


def bilibili(dry_run=False):
    """
    获取哔哩哔哩视频新闻
    :return: 新闻, 还能是什么?
    """

    """ 搜索视频 """

    # 搜索类型，这里指定为视频
    search_type = search.SearchObjectType.VIDEO
    # 排序类型，这里指定为发布时间
    order_type = search.OrderVideo.PUBDATE
    # 搜索关键字，这里指定为"游戏"
    video_zone_type = video_zone.VideoZoneTypes.GAME
    # 关键词
    keyword = "红石"
    # 页数
    page = 1

    # 过滤出最近1天的视频
    recent_videos = []
    # 时间限制
    target_time = time.time() - 86400
    print(f"搜索时间限制：{target_time}")

    print("正在搜索视频...")

    while page <= 25:
        print(f"正在搜索第{page}页...")

        # 调用搜索接口，获取搜索结果
        search_result = sync(search.search_by_type(
            keyword,
            search_type=search_type,
            order_type=order_type,
            video_zone_type=video_zone_type,
            page=page))

        # 遍历搜索结果，判断发布时间是否在最近1天内
        for video_item in search_result['result']:
            print(f"{video_item['pubdate']}")

            if video_item['pubdate'] > target_time:
                recent_videos.append(video_item)
            else:
                page = 999
                break

        time.sleep(1)
        page += 1

    for index in range(len(recent_videos)):
        # 处理标题数据, 删除HTML标签

        flag = False
        tmp_string = ''
        for i in recent_videos[index]['title']:
            if i == '<':
                flag = True
            if flag:
                if i == '>':
                    flag = False
                continue
            tmp_string += i
        recent_videos[index]['title'] = tmp_string

    """ 筛选视频 """

    for index in range(len(recent_videos)):
        # 通过关键词权重筛选视频

        # 创建一个权重,用于分析视频数据
        weight = 0.99

        for word in weight_map['terms']:
            if word in recent_videos[index]['title'] or word in recent_videos[index]['description'] or word in recent_videos[index]['tag']:
                weight *= 1.5

        for word in weight_map['blacklist']:
            if word in recent_videos[index]['title'] or word in recent_videos[index]['description'] or word in recent_videos[index]['tag']:
                weight = 0

        for word in weight_map['global']:
            if word['keyword'] in recent_videos[index]['title']:
                weight *= word['weight']
            if word['keyword'] in recent_videos[index]['description']:
                weight *= word['weight']
            if word['keyword'] in recent_videos[index]['tag']:
                weight *= word['weight']

        for word in weight_map['special']:
            if word['keyword'] in recent_videos[index]['title']:
                weight *= word['title'][0]
            if word['keyword'] in recent_videos[index]['description']:
                weight *= word['description'][0]
            if word['keyword'] in recent_videos[index]['tag']:
                weight *= word['tags'][0]
            if word['keyword'] not in recent_videos[index]['title']:
                weight *= word['title'][1]
            if word['keyword'] not in recent_videos[index]['description']:
                weight *= word['description'][1]
            if word['keyword'] not in recent_videos[index]['tag']:
                weight *= word['tags'][1]

        # 保存权重
        recent_videos[index]['weight'] = weight

    """ 结构化数据 """

    for index in range(len(recent_videos)):
        print(json.dumps(recent_videos[index]))

        structured_data = {
            'type': 'video',
            'title': recent_videos[index]['title'],
            'description': recent_videos[index]['description'],
            'cover': recent_videos[index]['pic'],
            'tag': recent_videos[index]['tag'],
            'pubdate': recent_videos[index]['pubdate'],
            'aid': recent_videos[index]['aid'],
            'bvid': recent_videos[index]['bvid'],
            'weight': recent_videos[index]['weight'],
            'date': time.strftime("%Y-%m-%d", time.localtime()),
            'data': {
                'play': recent_videos[index]['play'],
                'danmaku': recent_videos[index]['danmaku'],
                'like': recent_videos[index]['like'],
                'favorite': recent_videos[index]['favorites'],
                'review': recent_videos[index]['review'],
                'duration': recent_videos[index]['duration'],
                'score': (recent_videos[index]['like'] / (recent_videos[index]['play'] + 1)
                       + recent_videos[index]['danmaku'] / (recent_videos[index]['play'] + 1)
                       + recent_videos[index]['review'] / (recent_videos[index]['play'] + 1)
                       - recent_videos[index]['favorites'] / (recent_videos[index]['play'] + 1))
                       * recent_videos[index]['weight'],
                'owner': {
                    'author': recent_videos[index]['author'],
                    'face': recent_videos[index]['upic']
                }
            },
            'url': recent_videos[index]['arcurl']
        }

        # 保存数据
        recent_videos[index] = structured_data

    """ 保存数据 """

    if not dry_run:
        items = get_database().set_collection('news_items')
        for item in recent_videos:
            items.insert_one(item) if item['weight'] > 1 else None  # 权重大于1的才保存到数据库

        original = get_database().set_collection('original_items')
        for item in recent_videos:
            original.insert_one(item)

    return recent_videos


if __name__ == '__main__':
    print([i if i['weight'] > 1 else None for i in bilibili()])
