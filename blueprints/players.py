import re

from blueprints.steam import get_vanity_to_steam_id_or_random_response, \
    get_steam_profile_or_random_response

from flask import render_template, Blueprint, current_app, redirect, url_for, jsonify, request

from database.wrapper.player_wrapper import PlayerWrapper
from database.wrapper.stat_wrapper import PlayerStatWrapper
from helpers.functions import render_with_session, get_rank

bp = Blueprint('players', __name__, url_prefix='/players')
regex = re.compile('[0-9]{17}')

player_wrapper = PlayerWrapper()
player_stat_wrapper = PlayerStatWrapper(player_wrapper)


@bp.route('/overview/<id_>')  # ID must be always at the end
def view_player(id_):
    print(re.match(regex, id_))
    if len(id_) != 17 or re.match(regex, id_) is None:
        r = get_vanity_to_steam_id_or_random_response(id_, current_app)
        if r is None:
            return redirect(url_for('home'))
        id_ = r['response']['steamid']
        return redirect(url_for('players.view_player', id_=id_))
    session = current_app.config['db']()
    rank = get_rank(id_)
    total_games = player_wrapper.get_total_games(session, id_)
    games, stats, favorite_car, favorite_car_pctg = player_stat_wrapper.get_averaged_stats(session, id_, total_games)
    steam_profile = get_steam_profile_or_random_response(id_, current_app)
    if steam_profile is None:
        return render_template('error.html', error="Unable to find the requested profile")

    return render_with_session('player.html', session, games=games, rank=rank, profile=steam_profile, car=favorite_car,
                               favorite_car_pctg=favorite_car_pctg, stats=stats,
                               total_games=total_games,
                               id=id_, get_stat_spider_charts=PlayerStatWrapper.get_stat_spider_charts)


@bp.route('/overview/<id_>/compare', methods=['POST'])
def compare_player_redir(id_):
    print(request.form)
    other = request.form['other']
    if len(other) != 17 or re.match(regex, other) is None:
        r = get_vanity_to_steam_id_or_random_response(other, current_app)
        if r is None:
            return redirect(url_for('players.view_player', id_=id_))
        other = r['response']['steamid']
    return redirect(url_for('players.compare_player', ids=",".join([id_, other])))


@bp.route('/compare/<ids>')
def compare_player(ids):
    session = current_app.config['db']()
    ids = ids.split(',')
    common_games = player_wrapper.get_player_games(session, ids)
    users = []
    for player_id in ids:
        games, stats, favorite_car, favorite_car_pctg = player_stat_wrapper.get_averaged_stats(session, player_id)
        steam_profile = get_steam_profile_or_random_response(player_id, current_app)
        if steam_profile is None:
            return render_template('error.html', error="Unable to find the requested profile: " + player_id)
        user = {
            'id': player_id,
            'games': games,
            'stats': stats,
            'favorite_car': favorite_car,
            'favorite_car_pctg': favorite_car_pctg,
            'steam_profile': steam_profile
        }
        users.append(user)
    return render_with_session('compare.html', session, games=common_games, users=users,
                               get_stat_spider_charts=PlayerStatWrapper.get_stat_spider_charts)


@bp.route('/overview/<id_>/history/<page_number>')
def render_player_history(id_, page_number):
    page_number = int(page_number) - 1
    print(re.match(regex, id_))
    if len(id_) != 17 or re.match(regex, id_) is None:
        r = get_vanity_to_steam_id_or_random_response(id_)
        if r is None:
            return redirect(url_for('home'))
        id_ = r['response']['steamid']
        return redirect(url_for('players.view_player', id_=id_))
    session = current_app.config['db']()
    games = player_wrapper.get_player_games(session, id_, page=page_number)
    return jsonify({'html': render_template('partials/replay/match_history.html', games=games)})
