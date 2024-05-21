from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, url_for, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user


app = Flask(__name__)
app.secret_key = 'some secret salt'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///kursach.db'
app.app_context()

db = SQLAlchemy(app)
manager = LoginManager(app)


class Jury(db.Model):  #таблица бд для вошедших в игру членов жюри
    __tablename__ = 'juries'
    name = db.Column(db.String(100), nullable=False)
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    def __repr__(self):
        return f"<users {self.id}>"


class Player(db.Model):  #таблица бд для вошедших в игру участников (одиночная игра)
    __tablename__ = 'players'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(100), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    supergame_bet = db.Column(db.Integer, nullable=False)
    supergame_answer = db.Column(db.String, nullable=False)

    def __repr__(self):
        return f"<users {self.id}>"


class Team(db.Model):  #таблица бд для вошедших в игру участников (командная игра)
    __tablename__ = 'teams'
    id = db.Column(db.Integer, primary_key=True)
    name_teamleader = db.Column(db.String(100), unique=True)
    name_players = db.Column(db.String(300))
    name_team = db.Column(db.String(100))
    contact = db.Column(db.String(100))


    def __repr__(self):
        return f"<users {self.id}>"


class Manager(db.Model, UserMixin): #таблица бд для зарегистрировавшихся в приложении организаторов (в основном для создания игры)
    __tablename__ = 'organizators'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)
    games = db.relationship('Games', backref='manager', lazy=True)

    def __repr__(self):
        return f"<users {self.id}>"


class Games(db.Model):  #таблица бд для записи игр (я тут конечно строчки для записи кодов вставила, но они не работают, связывала (ну пыталась) таблицу games и codes через id игры)
    __tablename__ = 'games'
    id = db.Column(db.Integer, primary_key=True)
    id_manager = db.Column(db.Integer, db.ForeignKey('organizators.id'), nullable=False)
    name_game = db.Column(db.String(200), nullable=False)
    type_game = db.Column(db.String(200), nullable=False)
    type_players = db.Column(db.String(200), nullable=False)
    access_code = db.relationship('Codes', uselist=False, back_populates="game")
    hackathon_id = db.Column(db.Integer, db.ForeignKey('case.id'))

    @property
    def case(self):
        return Case.query.get_or_404(self.hackathon_id)

    def __repr__(self):
        return f"<Game {self.id} - {self.name_game}>"


class Case(db.Model): #таблица бд для кейса хакатона
    id = db.Column(db.Integer, primary_key=True)
    case_name = db.Column(db.String(200))
    case_description = db.Column(db.Text)
    criteria = db.relationship('Criteria', backref='case', lazy=True)

    def repr(self):
        return '<Case%r>' % self.id


class Criteria(db.Model): #таблица бд для критериев кейса хакатона
    id = db.Column(db.Integer, primary_key=True)
    criteria_name = db.Column(db.String(100))
    points = db.Column(db.Integer)
    id_case = db.Column(db.Integer, db.ForeignKey('case.id'), nullable=False)

    def repr(self):
        return '<Criteria%r>' % self.id


class Evaluation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)
    player = db.relationship('Player', backref='evaluations')
    case_id = db.Column(db.Integer, db.ForeignKey('case.id'), nullable=False)
    case = db.relationship('Case', backref='evaluations')
    jury_id = db.Column(db.Integer, db.ForeignKey('juries.id'), nullable=False)
    jury = db.relationship('Jury', backref='evaluations')
    points = db.Column(db.Integer)

    def __repr__(self):
        return f"<Evaluation object with id {self.id}>"

    # Метод для добавления баллов за критерий
    def add_criterion_score(self, criterion, score):
        if not hasattr(self, 'criterion_scores'):
            self.criterion_scores = []
        self.criterion_scores.append({'criterion': criterion, 'score': int(score)})

    # Метод для получения всех баллов за критерии
    def get_all_criterion_scores(self):
        return self.criterion_scores

    # Метод для получения общего количества баллов
    def get_total_score(self):
        return sum(score['score'] for score in self.criterion_scores)

    # Метод для обновления оценки, если она уже существует
    def update_evaluation(self, existing_criterion, score):
        if any(criterion['criterion'] == existing_criterion for criterion in self.get_all_criterion_scores):
            # Критерий уже существует, обновляем его счет
            for criterion in self.criterion_scores:
                if criterion['criterion'] == existing_criterion:
                    criterion['score'] = int(score)
        else:
            self.criterion_scores.append({'criterion': existing_criterion, 'score': int(score)})
        self.points = sum(score['score'] for score in self.criterion_scores)



class Codes(db.Model): #таблица бд для кодов жюри и игроков при создании игры
    id = db.Column(db.Integer, primary_key=True,  nullable=False, autoincrement=True)
    code_jury = db.Column(db.String(100), unique=True)
    code_players = db.Column(db.String(100), unique=True)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), nullable=False, unique=True)
    game = db.relationship("Games", back_populates="access_code")

    def __repr__(self):
        return f"<users {self.id}>"


class PlayerCodesAssociation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'))
    codes_id = db.Column(db.Integer, db.ForeignKey('codes.id'))
    player = db.relationship("Player")
    codes = db.relationship("Codes")

    def repr(self):
        return '<PlayerCodesAssociation%r>' % self.id


class Question(db.Model):
    __tablename__ = 'questions'
    id = db.Column(db.Integer, primary_key=True)
    cost = db.Column(db.Integer, nullable=False)
    question = db.Column(db.String, nullable=False)
    answer = db.Column(db.String, nullable=False)

    def __repr__(self):
        return '<Question%r>' % self.id


class Theme(db.Model):
    __tablename__ = 'themes'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)

    def __repr__(self):
        return '<Theme%r>' % self.id


class Superquestion(db.Model):
    __tablename__ = 'superquestions'
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String, nullable=False)
    answer = db.Column(db.String, nullable=False)
    theme = db.Column(db.String, nullable=False)

    def __repr__(self):
        return '<Superquestion%r>' % self.id


class GameTheme(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column( db.Integer, db.ForeignKey('games.id'))
    theme_id = db.Column(db.Integer, db.ForeignKey('themes.id'))


class GameQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column( db.Integer, db.ForeignKey('games.id'))
    question_id = db.Column( db.Integer, db.ForeignKey('questions.id'))


class GameSuperquestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'))
    superquestion_id = db.Column(db.Integer, db.ForeignKey('superquestions.id'))


class Question1(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cost = db.Column(db.Integer, nullable=False)
    question = db.Column(db.String, nullable=False)
    answer = db.Column(db.String, nullable=False)
    wrong_answer1 = db.Column(db.String, nullable=False)
    wrong_answer2 = db.Column(db.String, nullable=False)
    wrong_answer3 = db.Column(db.String, nullable=False)

    def __repr__(self):
        return '<Question1%r>' % self.id



with app.app_context():
    db.create_all()


@manager.user_loader  #это нужно для регистрации и авторизации
def load_user(user_id):
    return Manager.query.get(user_id)


@app.route('/')
def index():
    return render_template("home.html")


@app.route('/about') #страница про нас
def about():
    return render_template("about.html")


@app.route('/user/<string:name>/<int:id>') #аааа ??? я хз но это нужно??? наверное...
def user(name, id):
    return "User page: " + name + " - " + str(id)


@app.route('/instruction') #страница с инструкцией по приложению
def instruction():
    return render_template("instruction.html")


@app.route('/jury', methods=["POST", "GET"]) #тут члены жюри входят в игру
def jury():
    if request.method == "POST":
        code = request.form['psw']
        check_code = Codes.query.filter_by(code_jury=code).first()
        if check_code:
            namee = request.form['name']
            jury = Jury(name=namee)
            db.session.add(jury)
            db.session.commit()
            session['jury_id'] = jury.id  # Сохраняем ID жюри в сессию
            game_id = check_code.game_id
            type_game = (Games.query.get(game_id)).type_game
            type_players = (Games.query.get(game_id)).type_players
            session['codes_id'] = check_code.id
            if type_game == "Хакатон" and type_players == "Одиночная игра":
                return redirect('/jury_participants')
            return redirect(url_for('about')) #здесь должны переходить не на about, а на определенную игру, которая привязана к определенному коду

        else:
            return render_template('jury_error.html') #переходим на страницу где выплывает красная табличка с ошибкой, если код игры не совпадает с введенным кодом
    else:
        db.session.rollback()
    return render_template('jury.html')


@app.route('/player', methods=["POST", "GET"]) #тут игроки (одиночная игра) входят в игру
def player():
    if request.method == "POST":
        code = request.form['psw']
        check_code = Codes.query.filter_by(code_players=code).first()
        session['codes_id'] = check_code
        if check_code:
            namee = request.form['name']
            contactt = request.form['contact']
            new_player = Player(name=namee, contact=contactt, score=0, supergame_bet=0, supergame_answer="ответ")
            db.session.add(new_player)
            db.session.commit()
            # Добавляем связь между новым игроком и кодом
            player_codes_association = PlayerCodesAssociation(player_id=new_player.id, codes_id=check_code.id)
            db.session.add(player_codes_association)
            db.session.commit()
            game_id = check_code.game_id
            type_game = (Games.query.get(game_id)).type_game
            if type_game == "Хакатон":
                return redirect('/view_for_participants/{}'.format(game_id))
            if type_game == "Своя игра":
                return redirect('/ongoing_game')
        else:
            return render_template('player_error.html') #переходим на страницу где выплывает красная табличка с ошибкой, если код игры не совпадает с введенным кодом
    else:
        db.session.rollback()
    return render_template('player.html')


@app.route('/teamleader', methods=["POST", "GET"]) #тут игроки (командная игра) входят в игру
def teamleader():
    if request.method == "POST":
        hash = generate_password_hash(request.form['psw'])
        if check_password_hash(hash, '0000') == True:
            namee_teamleader = request.form["teamleader"]
            namee_players = request.form['players']
            namee_team = request.form['team']
            contactt = request.form['contact']
            db.session.add(Team(name_teamleader=namee_teamleader, name_players=namee_players, name_team=namee_team, contact=contactt))
            db.session.commit()

            return redirect(url_for('about')) #здесь должны переходить не на about, а на определенную игру, которая привязана к определенному коду

        else:
            return render_template('teamleader_error.html') #переходим на страницу где выплывает красная табличка с ошибкой, если код игры не совпадает с введенным кодом
    else:
        db.session.rollback()
    return render_template('teamleader.html')


@app.route('/manager') #тут страница где организатор выбирает: войти в существующий аккаунт или создать новый аккаунт
def manager():
    return render_template("manager.html")


@app.route('/manager_new_account', methods=["POST", "GET"]) #тут организатор создает новый аккаунт
def manager_new_account():
    if request.method == "POST":
        hash = generate_password_hash(request.form['psw'])
        psw_confirm = request.form['psw_confirm']
        if check_password_hash(hash, psw_confirm) == True:
            namee = request.form["name"]
            email = request.form['email']
            db.session.add(Manager(name=namee, email=email, password=hash))
            db.session.commit()

            return redirect(url_for('manager_account')) #после регистрации сразу перебрасываем на вход в существующий аккаунт чтобы было удобнее

        else:
            return render_template('manager_new_account_error.html') #переходим на страницу где выплывает красная табличка с ошибкой, если пароль не совпадает с повторением пароля
    else:
        db.session.rollback()
    return render_template("manager_new_account.html")


@app.route('/manager_account', methods=["POST", "GET"]) #тут организатор входит в уже существующий аккаунт
def manager_account():
    email = request.form.get('email_manager', 'my default')
    password = request.form.get('psw', 'my default')

    if email and password:
        user = Manager.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password) is True:
            login_user(user)
            return redirect(url_for('manager_menu')) #при успешной авторизации переходим в меню организатора

    return render_template("manager_account.html")


@app.route('/manager_menu') #тут меню организатора где он выбирает: создать новую игру, открыть архив завершенных игр или открыть таблицу с активными играми
def manager_menu():
    return render_template("manager_menu.html")


@app.route('/manager_new_game', methods=["POST", "GET"]) #тут организатор создает новую игру (вводит название и выбирает тип игры (хакатон, квиз, своя игра + одиночная или командная игра)
def manager_new_game():
    if request.method == "POST":

        namee_manager = request.form['name_manager']
        namee_game = request.form['name_game']

        options = request.form.get('options')
        if options == 'option1':
            typee_game = 'Хакатон'
        elif options == 'option2':
            typee_game = 'Квиз'
        elif options == 'option3':
            typee_game = 'Своя игра'

        optionss = request.form.get('optionss')
        if optionss == 'option4':
            typee_players = 'Одиночная игра'
        elif optionss == 'option5':
            typee_players = 'Командная игра'
        # Найдем объект Manager по имени
        manager = Manager.query.filter_by(name=namee_manager).first()
        new_game = Games(id_manager=manager.id, name_game=namee_game, type_game=typee_game, type_players=typee_players, hackathon_id=-1)
        db.session.add(new_game)
        db.session.commit()
        game_id = new_game.id
        session['game_id'] = game_id
        if typee_game == 'Хакатон':
            return redirect(url_for('add_case')) #пока что здесь редиректим на хакатон, но вообще должны как-то фильтровать: выбрали квиз-адресуем на создание квиза и тд
        if typee_game == 'Своя игра':
            return redirect(url_for('game_creation_begin'))
        if typee_game =='Квиз':
            return redirect(url_for('quiz_index'))
    else:
        db.session.rollback()

    return render_template('manager_new_game.html')


@app.route('/add_case')
def add_case():
    return render_template('add_case.html')


@app.route('/save_case', methods=['POST'])
def save_case():
    case_name = request.form['case_name']
    case_description = request.form['description']

    new_case = Case(case_name=case_name, case_description=case_description)
    db.session.add(new_case)
    game_id = session.get('game_id')
    game = Games.query.filter_by(id=game_id).first()
    game.hackathon_id = new_case.id
    criteria_names = request.form.getlist('criteria')
    points_list = request.form.getlist('points')

    for i in range(len(criteria_names)):
        new_criteria = Criteria(criteria_name=criteria_names[i], points=int(points_list[i]), case=new_case)
        db.session.add(new_criteria)

    db.session.commit()

    return redirect('/view_case/{}'.format(new_case.id))


@app.route('/view_case/<int:case_id>')
def view_case(case_id):
    case = Case.query.get(case_id)
    return render_template("index.html", case = case)


@app.route('/view_for_participants/<int:case_id>')
def view_for_participants(case_id):
    case = Case.query.get(case_id)
    criteria = Criteria.query.filter_by(case=case).all()
    return render_template("view_for_participants.html", case=case, criteria=criteria)


@app.route('/jury_participants')
def participants():
    a = {}
    code = session.get('codes_id')
    codes_id = PlayerCodesAssociation.query.filter_by(codes_id=code).all()
    i = 1
    for code_id in codes_id:
        player = Player.query.get(code_id.player_id)
        a[i] = player.name if player else None
        i+=1
    session['players'] = a
    return render_template("participants.html", slovar=a)


@app.route('/jury_№participant', methods=['GET', 'POST'])
def participantss():
    code_id = session.get('codes_id')
    code = Codes.query.get(code_id)
    game = Games.query.get(code.game_id)
    case = Case.query.get(game.hackathon_id)
    session['case_id'] = case.id
    player_number = request.args.get('player_number')
    igrok = session.get('players').get(int(player_number))
    session['igrok'] = player_number
    return render_template("dlya№.html", case=case, igrok=igrok,player_number=player_number)


@app.route('/save_data', methods=['GET', 'POST'])
def process_form():
    if request.method == 'POST':
        # Получаем все значения input элементов с именем 'participant_score'
        igrok = session.get('igrok')
        participant_scores = request.form.getlist('participant_score')
        player = Player.query.filter_by(id=igrok).first()
        case_id = session.get('case_id')
        case = Case.query.get(case_id)
        jury_id = session.get("jury_id")
        # Проверяем, есть ли уже оценка для данного игрока и данного члена жюри
        existing_evaluation = Evaluation.query.filter_by(player_id=player.id, case_id=case.id, jury_id=jury_id).first()
        if player:
            if existing_evaluation:
                for criterion, score in zip(case.criteria, participant_scores):
                    existing_evaluation.update_evaluation(criterion.criteria_name, score)
            else:
                # Если оценки нет, создаем новую
                new_evaluation = Evaluation(player_id=player.id, case_id=case.id, points=0, jury_id=jury_id, criterion_scores=[])
                # Добавляем баллы за критерии
                for criterion, score in zip(case.criteria, participant_scores):
                    new_evaluation.add_criterion_score(criterion.criteria_name, score)
                # Сохраняем новый экземпляр в базу данных
                db.session.add(new_evaluation)
                total_score = new_evaluation.get_total_score()
                player.score = total_score
                new_evaluation.points = total_score
        db.session.commit()
        return redirect(url_for('participants'))


@app.route('/jury_participants_general_table')
def table():
    return render_template("obshaya_tablica1.html")


@app.route('/jury_teams')
def team():
    return render_template("comandsextend.html")


@app.route('/jury_№team')
def teamss():
    return render_template("dlyacom1.html")


@app.route('/jury_general_table_for_teams')
def tableteam():
    return render_template("comtablext.html")


@app.route('/results_for_participants')
def respart():
    return render_template("respart.html")


@app.route('/results_for_participant')
def respartconcrete():
    return render_template("part.html")


@app.route('/results_for_teams')
def resteam():
    return render_template("resteam.html")


@app.route('/results_for_team')
def resteamconcrete():
    return render_template("team.html")


@app.route('/create_code', methods=["POST", "GET"]) #тут организатор после создания игры создаем коды
def create_code():
    if request.method == "POST":
        game_idd = session.get('game_id')
        codee_jury = request.form['code_jury']
        codee_players = request.form['code_players']

        db.session.add(Codes(code_jury=codee_jury, code_players=codee_players, game_id=game_idd, team_id=0))
        db.session.commit()

        return redirect(url_for('manager_menu')) #редиректим в меню организатора (пушта вдруг он захочет создать еще одну игру)
    return render_template("create_code.html")


@app.route('/game_creation_begin')
def game_creation_begin():
    return render_template("game_creation_begin.html", )


@app.route('/super_game_creation')
def super_game_creation():
    return render_template("super_game_creation.html")


@app.route('/super_game_creation/add_question', methods=['GET', 'POST'])
def super_game_creation_add_question():
    if request.method == 'POST':
        question = request.form['question']
        answer = request.form['answer']
        theme = request.form['theme']
        game_id = session.get('game_id')
        superquestion = Superquestion(question=question, answer=answer, theme=theme)
        db.session.add(superquestion)
        db.session.commit()
        game_superquestion = GameSuperquestion(game_id=game_id, superquestion_id=superquestion.id)
        db.session.add(game_superquestion)
        db.session.commit()
        return redirect('/super_game_creation')
    else:
        return render_template("super_game_creation_add_question.html")


@app.route('/game_creation')
def game_creation():
    return render_template("game_creation.html", )


@app.route('/input_theme', methods=['GET', 'POST'])
def input_theme():
    if request.method == 'POST':
        name = request.form['name']
        theme = Theme(name=name)
        game_id = session.get('game_id')
        try:
            db.session.add(theme)
            db.session.commit()
            game_theme = GameTheme(game_id=game_id, theme_id=theme.id)
            db.session.add(game_theme)
            db.session.commit()
            return redirect('/game_creation')

        except:
            return "Произошла ошибка при добавлении вопроса, попробуйте проверить правильность введенны данных"
    else:
        return render_template('input_theme.html')


@app.route('/input_question_info', methods=['POST', 'GET'])
def input_question_info():
    if request.method == 'POST':
        cost = request.form['cost']
        question = request.form['question']
        answer = request.form['answer']
        game_id = session.get('game_id')
        task = Question(cost=cost, question=question, answer=answer)
        try:
            db.session.add(task)
            db.session.commit()
            game_question = GameQuestion(game_id=game_id, question_id=task.id)
            db.session.add(game_question)
            db.session.commit()
            return redirect('/game_creation')

        except:
            return "Произошла ошибка при добавлении вопроса, попробуйте проверить правильность введенны данных"
    else:
        return render_template('input_question_info.html')


@app.route('/show_all_questions')
def show_all_questions():
    questions = Question.query.order_by(Question.id).all()
    themes = Theme.query.order_by(Theme.id).all()
    return render_template('show_all_questions.html', questions=questions, themes=themes)


@app.route('/show_all_superquestions')
def show_all_superquestions():
    questions = Superquestion.query.order_by(Superquestion.id).all()
    return render_template('show_all_superquestions.html', questions=questions)


@app.route('/show_all_superquestions/<int:id>')
def show_all_superquestions_detail(id):
    question = Superquestion.query.get(id)
    return render_template('superquestion_detail.html', question=question)


@app.route('/show_all_questions/<int:id>')
def show_all_questions_detail(id):
    question = Question.query.get(id)
    return render_template('question_detail.html', question=question)


@app.route('/show_all_questions/<int:id>/del')
def question_delete(id):
    question = Question.query.get_or_404(id)
    game_question = GameQuestion.query.filter_by(question_id=id).first()
    try:
        db.session.delete(question)
        db.session.delete(game_question)
        db.session.commit()
        return redirect('/show_all_questions')
    except:
        return "При удалении вопроса произошла ошибка"


@app.route('/show_all_questions/<int:id>/upd', methods=['POST', 'GET'])
def question_update(id):
    question = Question.query.get(id)
    if request.method == 'POST':
        question.cost = request.form['cost']
        question.question = request.form['question']
        question.answer = request.form['answer']

        try:
            db.session.commit()
            return redirect('/game_creation')

        except:
            return "Произошла ошибка при добавлении вопроса, попробуйте проверить правильность введенны данных"
    else:
        return render_template('question_update.html', question=question)


@app.route('/show_all_superquestions/<int:id>/upd', methods=['POST', 'GET'])
def superquestion_update(id):
    question = Superquestion.query.get(id)
    if request.method == 'POST':
        question.theme = request.form['theme']
        question.question = request.form['question']
        question.answer = request.form['answer']

        try:
            db.session.commit()
            return redirect('/show_all_superquestions')

        except:
            return "Произошла ошибка при обновлении вопроса, попробуйте проверить правильность введенны данных"
    else:
        return render_template('superquestion_update.html', question=question)


@app.route('/show_all_superquestions/<int:id>/del')
def superquestion_delete_super(id):
    superquestion = Superquestion.query.get_or_404(id)
    game_superquestion = GameSuperquestion.query.filter_by(superquestion_id=id).first()
    try:
        db.session.delete(superquestion)
        db.session.delete(game_superquestion)
        db.session.commit()
        return redirect('/show_all_superquestions')
    except:
        return "При удалении вопроса произошла ошибка"


@app.route('/ongoing_game')
def ongoing_game():
    game_id = session.get('game_id')
    game_questions = GameQuestion.query.filter_by(game_id=game_id).all()
    questions = Question.query.filter(Question.id.in_(
        [game_question.question_id for game_question in game_questions]
    )).all()
    game_themes = GameTheme.query.filter_by(game_id=game_id).all()
    themes = Theme.query.filter(Theme.id.in_(
        [game_theme.theme_id for game_theme in game_themes]
    )).all()

    a = {}
    code = session.get('codes_id')
    codes_id = PlayerCodesAssociation.query.filter_by(codes_id=code).all()
    i = 1
    for code_id in codes_id:
        player = Player.query.get(code_id.player_id)
        a[i] = player.name if player else None
        i += 1
    session['players'] = a
    players = a
    return render_template("ongoing_game.html", questions=questions, themes=themes, players=players)


@app.route('/ongoing_game2')
def ongoing_game2():
    questions = Question.query.order_by(Question.id).all()
    themes = Theme.query.order_by(Theme.id).all()
    players = Player.query.order_by(Player.id).all()
    return render_template("ongoing_game2.html", questions=questions, themes=themes, players=players)


@app.route('/supergame', methods=['POST', 'GET'])
def supergame():
    questions = Superquestion.query.order_by(Superquestion.id).all()
    themes = Theme.query.order_by(Theme.id).all()
    players = Player.query.order_by(Player.id).all()
    return render_template("supergame.html", questions=questions, themes=themes, players=players)


@app.route('/supergame/<int:id>/del')
def superquestion_delete(id):
    question = Superquestion.query.get_or_404(id)
    game_superquestion = GameSuperquestion.query.get_or_404(superquestion_id=id)
    try:
        db.session.delete(question)
        db.session.delete(game_superquestion)
        db.session.commit()
        return redirect('/supergame')
    except:
        return "При удалении вопроса произошла ошибка"


@app.route('/supergame/<int:id>')
def ongoing_game_superquestion(id):
    question = Superquestion.query.get(id)
    players = Player.query.order_by(Player.id).all()
    return render_template('Superquestion_game.html', question=question, players=players)


@app.route('/supergame/<int:id>/answer', methods=['POST', 'GET'])
def ongoing_game_superquestion_answer(id):
    question = Superquestion.query.get(id)
    players = Player.query.order_by(Player.id).all()
    return render_template('Superquestion_game_answer.html', question=question, players=players)


@app.route('/supergame/<int:question_id>/answer/true/<int:player_id>', methods=['POST', 'GET'])
def ongoing_game_superquestion_answer_true(question_id, player_id):
    player = Player.query.get(player_id)
    player.score += player.supergame_bet
    try:
        db.session.commit()
        return redirect('/supergame')
    except:
        return "При удалении вопроса произошла ошибка"


@app.route('/supergame/<int:question_id>/answer/false/<int:player_id>', methods=['POST', 'GET'])
def ongoing_game_superquestion_answer_false(question_id, player_id):
    player = Player.query.get(player_id)
    player.score -= player.supergame_bet
    try:
        db.session.commit()
        return redirect('/supergame')
    except:
        return "При удалении вопроса произошла ошибка"


@app.route('/supergame/<int:question_id>/supergame_bet/<int:player_id>', methods=['POST', 'GET'])
def supergame_bet(question_id, player_id):
    question = Superquestion.query.get(question_id)
    player = Player.query.get(player_id)

    if request.method == 'POST':
        player.supergame_bet = request.form['bet']
        try:
            db.session.commit()
            return redirect(url_for('supergame', id=question_id))
        except:
            return "Произошла bebra"

    return render_template('supergame_bet.html', question=question, player=player)


@app.route('/ongoing_game/<int:id>', methods=['POST', 'GET'])
def ongoing_game_question(id):
    question = Question.query.get(id)
    players = Player.query.order_by(Player.id).all()
    nazad = request.form.get('pravda')
    if request.method == 'POST':
        if nazad == "true":
            question.cost = "   "
        try:
            db.session.commit()
            return redirect(url_for('ongoing_game'))
        except:
            return "Произошла bebra"

    return render_template('question_game.html', question=question, players=players)


@app.route('/ongoing_game/<int:id>/answer')
def ongoing_game_answer(id):
    question = Question.query.get(id)
    return render_template('question_answer.html', question=question)


@app.route('/ongoing_game/<int:question_id>/true_or_false/<int:player_id>', methods=['POST', 'GET'])
def nikita_petrov(question_id, player_id):
    question = Question.query.get(question_id)
    players = Player.query.order_by(Player.id).all()
    true_or_false = request.form.get('pravda')
    cost_question = Question.query.get(question_id)
    score_player = Player.query.get(player_id)

    if request.method == 'POST':
        if true_or_false == "true":
            score_player.score += cost_question.cost
            cost_question.cost = "   "


        elif true_or_false == "false":
            score_player.score -= cost_question.cost

        try:
            db.session.commit()
            if true_or_false == "true":
               return redirect('/ongoing_game/{}/answer'.format(question.id))
            elif true_or_false == "false":
                return redirect('/ongoing_game/{}'.format(question.id))

        except:

            return "Произошла bebra"

    return render_template('true_or_false.html', question=question, player=players)


@app.route('/registration', methods=['GET', 'POST'])
def registration():
    if request.method == 'POST':
        name = request.form['name']
        new_player = Player(name=name, contact="net", score=0, supergame_bet=0, supergame_answer="ответ")
        db.session.add(new_player)
        db.session.commit()
        return redirect('/game_creation_begin')

    else:
        return render_template('registration.html')


@app.route('/player_update_creation/<int:id>')
def show_all_questions__player_detail(id):
    player = Player.query.get(id)
    return render_template('player_update_creation.html', player=player)

@app.route('/player_update_creation/<int:id>/del')
def player_delete(id):
    player = Player.query.get_or_404(id)
    try:
        db.session.delete(player)
        db.session.commit()
        return redirect('/show_all_questions')
    except:
        return "При удалении игрока произошла ошибка"

@app.route('/player_update_creation/<int:id>/upd', methods=['POST', 'GET'])
def player_update_nickname(id):
    player = Player.query.get(id)
    if request.method == 'POST':
        player.name = request.form['name']


        try:
            db.session.commit()
            return redirect('/game_creation')

        except:
            return "Произошла ошибка при добавлении вопроса, попробуйте проверить правильность введенны данных"
    else:
        return render_template('player_change_nickname.html', player=player)

@app.route('/quiz')
def quiz_index():
    return render_template('quiz_index.html')


@app.route('/quiz_registration', methods=['GET', 'POST'])
def quiz_registration():
    if request.method == 'POST':
        name = request.form['name']
        score = 0
        player = Player(name=name, score=score)

        try:
            db.session.add(player)
            db.session.commit()
            return redirect('/')

        except:

            return "Произошла ошибка при регистрации"

    return render_template('quiz_registration.html')


@app.route('/quiz_game_creation_begin')
def quiz_game_creation_begin():
    return render_template("quiz_game_creation_begin.html", )


@app.route('/quiz_game_creation')
def quiz_game_creation():
    return render_template("quiz_game_creation.html", )


@app.route('/quiz_input_question_info', methods=['POST', 'GET'])
def quiz_input_question_info():
    if request.method == 'POST':
        cost = request.form['cost']
        question = request.form['question']
        answer = request.form['answer']
        wrong_answer1 = request.form['wrong_answer1']
        wrong_answer2 = request.form['wrong_answer2']
        wrong_answer3 = request.form['wrong_answer3']
        task = Question1(cost=cost, question=question, answer=answer, wrong_answer1=wrong_answer1, wrong_answer2=wrong_answer2, wrong_answer3=wrong_answer3)
        db.session.add(task)
        db.session.commit()
        return redirect('/quiz_game_creation')
    else:
        return render_template('quiz_input_question_info.html')


@app.route('/quiz_show_all_questions')
def quiz_show_all_questions():
    questions = Question1.query.order_by(Question1.id).all()
    return render_template('quiz_show_all_questions.html', questions=questions)


@app.route('/quiz_show_all_questions/<int:id>')
def quiz_show_all_questions_detail(id):
    question = Question1.query.get(id)
    return render_template('quiz_question_detail.html', question=question)


@app.route('/quiz_show_all_questions/<int:id>/del')
def quiz_question_delete(id):
    question = Question1.query.get_or_404(id)
    try:
        db.session.delete(question)
        db.session.commit()
        return redirect('/quiz_show_all_questions')
    except:
        return "Ошибка при удалении вопроса"


@app.route('/quiz_show_all_questions/<int:id>/upd', methods=['POST', 'GET'])
def quiz_question_update(id):
    question = Question1.query.get(id)
    if request.method == 'POST':
        question.cost = request.form['cost']
        question.question = request.form['question']
        question.answer = request.form['answer']
        question.wrong_answer1 = request.form['wrong_answer1']
        question.wrong_answer2 = request.form['wrong_answer2']
        question.wrong_answer3 = request.form['wrong_answer3']


        try:
            db.session.commit()
            return redirect('/quiz_game_creation')

        except:
            return "Произошла ошибка при добавлении вопроса"
    else:
        return render_template('quiz_question_update.html', question=question)


@app.route('/quiz_ongoing_game')
def quiz_ongoing_game():
    questions = Question1.query.order_by(Question1.id).all()
    players = Player.query.order_by(Player.id).all()
    return render_template("quiz_ongoing_game.html", questions=questions, players=players)


@app.route('/quiz_ongoing_game/<int:id>')
def quiz_ongoing_game_question(id):
    question = Question1.query.get(id)
    players = Player.query.order_by(Player.id).all()
    return render_template('quiz_question_game.html', question=question,  players=players)


@app.route('/quiz_ongoing_game/<int:question_id>/true_or_false/<int:player_id>', methods=['POST', 'GET'])
def quiz_game(question_id, player_id):
    question = Question1.query.get(question_id)
    answer = Question1.query.get(question_id)
    players = Player.query.order_by(Player.id).all()
    true_or_false = request.form.get('pravda')
    cost_question = Question1.query.get(question_id)
    score_player = Player.query.get(player_id)
    print(cost_question.cost, score_player.score)
    if request.method == 'POST':
        if true_or_false == "true":
            score_player.score += cost_question.cost

        elif true_or_false == "false":
            score_player.score -= cost_question.cost
        try:
            db.session.commit()
            return redirect('/quiz_ongoing_game')

        except:
            return "Произошла ошибка"
        print(cost_question.cost, score_player.score)

    return render_template('quiz_true_or_false.html', question=question, player=players)





if __name__ == "__main__":
    app.run(debug=True)