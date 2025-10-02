
-- Lookup / Reference tables

CREATE TABLE activity_level (
    id SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code VARCHAR(32) NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE objective_type (
    id SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code VARCHAR(32) NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE gender_type (
    id SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code VARCHAR(16) NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE dietary_restriction_type (
    id SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code VARCHAR(64) NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE meal_type (
    id SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code VARCHAR(32) NOT NULL UNIQUE,
    description TEXT
);



-- Core user & auth tables

CREATE TABLE "user_account" (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email VARCHAR(320) NOT NULL UNIQUE,
    full_name VARCHAR(200),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE auth_credential (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES user_account(id) ON DELETE CASCADE,
    password_hash TEXT NOT NULL,
    salt TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    last_login_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(user_id)
);

CREATE TABLE email_verification (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES user_account(id) ON DELETE CASCADE,
    token VARCHAR(128) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    verified_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE two_factor (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES user_account(id) ON DELETE CASCADE,
    totp_secret TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);


-- Profile & preferences

CREATE TABLE user_profile (
    user_id BIGINT PRIMARY KEY REFERENCES user_account(id) ON DELETE CASCADE,
    birth_date DATE,
    gender_id SMALLINT REFERENCES gender_type(id) ON DELETE SET NULL,
    height_cm NUMERIC(5,2),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE TABLE user_activity (
    user_id BIGINT NOT NULL REFERENCES user_account(id) ON DELETE CASCADE,
    activity_level_id SMALLINT NOT NULL REFERENCES activity_level(id) ON DELETE RESTRICT,
    effective_from DATE NOT NULL DEFAULT CURRENT_DATE,
    effective_to DATE,
    PRIMARY KEY (user_id, activity_level_id, effective_from),
    CHECK (effective_to IS NULL OR effective_to >= effective_from)
);

CREATE TABLE user_objective (
    user_id BIGINT PRIMARY KEY REFERENCES user_account(id) ON DELETE CASCADE,
    objective_type_id SMALLINT NOT NULL REFERENCES objective_type(id) ON DELETE RESTRICT,
    target_weight_kg NUMERIC(6,2),
    start_date DATE NOT NULL DEFAULT CURRENT_DATE,
    target_date DATE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);



-- Food items & preferences


CREATE TABLE food_item (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(256) NOT NULL,
    description TEXT,
    unit VARCHAR(32) NOT NULL DEFAULT 'g',
    calories_per_100g NUMERIC(10,3),
    protein_g_per_100g NUMERIC(10,3),
    carbs_g_per_100g NUMERIC(10,3),
    fats_g_per_100g NUMERIC(10,3),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    UNIQUE (name)
);

CREATE TABLE user_food_preference (
    user_id BIGINT NOT NULL REFERENCES user_account(id) ON DELETE CASCADE,
    food_item_id BIGINT NOT NULL REFERENCES food_item(id) ON DELETE RESTRICT,
    preference SMALLINT NOT NULL,
    noted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, food_item_id),
    CHECK (preference IN (-1,0,1))
);

CREATE TABLE user_dietary_restriction (
    user_id BIGINT NOT NULL REFERENCES user_account(id) ON DELETE CASCADE,
    restriction_id SMALLINT NOT NULL REFERENCES dietary_restriction_type(id) ON DELETE RESTRICT,
    noted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, restriction_id)
);


-- Recipes and composition

CREATE TABLE recipe (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title VARCHAR(300) NOT NULL,
    description TEXT,
    servings NUMERIC(6,2) NOT NULL DEFAULT 1,
    calories_per_serving NUMERIC(10,3),
    protein_g_per_serving NUMERIC(10,3),
    carbs_g_per_serving NUMERIC(10,3),
    fats_g_per_serving NUMERIC(10,3)
);

CREATE TABLE recipe_ingredient (
    recipe_id BIGINT NOT NULL REFERENCES recipe(id) ON DELETE CASCADE,
    food_item_id BIGINT NOT NULL REFERENCES food_item(id) ON DELETE RESTRICT,
    quantity NUMERIC(12,4) NOT NULL,
    unit VARCHAR(32) NOT NULL,
    PRIMARY KEY (recipe_id, food_item_id)
);


-- Plans, days, meals and composition

CREATE TABLE plan (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES user_account(id) ON DELETE CASCADE,
    title VARCHAR(200),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    start_date DATE,
    end_date DATE,
    total_calories_per_day NUMERIC(9,2),
    total_protein_g_per_day NUMERIC(9,2),
    notes TEXT
);

CREATE TABLE plan_day (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    plan_id BIGINT NOT NULL REFERENCES plan(id) ON DELETE CASCADE,
    day_of_week SMALLINT NOT NULL CHECK (day_of_week BETWEEN 1 AND 7),
    UNIQUE (plan_id, day_of_week)
);

CREATE TABLE plan_meal (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    plan_day_id BIGINT NOT NULL REFERENCES plan_day(id) ON DELETE CASCADE,
    meal_type_id SMALLINT NOT NULL REFERENCES meal_type(id) ON DELETE RESTRICT,
    meal_order SMALLINT NOT NULL CHECK (meal_order > 0),
    notes TEXT,
    UNIQUE (plan_day_id, meal_type_id, meal_order)
);

CREATE TABLE plan_meal_recipe (
    plan_meal_id BIGINT NOT NULL REFERENCES plan_meal(id) ON DELETE CASCADE,
    recipe_id BIGINT NOT NULL REFERENCES recipe(id) ON DELETE RESTRICT,
    servings NUMERIC(6,2) NOT NULL DEFAULT 1,
    PRIMARY KEY (plan_meal_id, recipe_id)
);

CREATE TABLE user_saved_plan (
    user_id BIGINT NOT NULL REFERENCES user_account(id) ON DELETE CASCADE,
    plan_id BIGINT NOT NULL REFERENCES plan(id) ON DELETE CASCADE,
    saved_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    is_favorite BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (user_id, plan_id)
);


-- Progress, adherence y feedback

CREATE TABLE progress_measurement (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES user_account(id) ON DELETE CASCADE,
    measured_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    weight_kg NUMERIC(6,2),
    body_fat_percent NUMERIC(5,2),
    waist_cm NUMERIC(6,2),
    hip_cm NUMERIC(6,2),
    chest_cm NUMERIC(6,2),
    notes TEXT
);

CREATE TABLE plan_feedback (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES user_account(id) ON DELETE CASCADE,
    plan_id BIGINT NOT NULL REFERENCES plan(id) ON DELETE CASCADE,
    rating SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE TABLE plan_adherence (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    plan_id BIGINT NOT NULL REFERENCES plan(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES user_account(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    adherence_percent NUMERIC(5,2) CHECK (adherence_percent BETWEEN 0 AND 100),
    notes TEXT,
    UNIQUE (plan_id, user_id, date)
);


-- Indices

CREATE INDEX idx_recipe_title ON recipe (title);
CREATE INDEX idx_food_item_name ON food_item (name);
CREATE INDEX idx_user_email ON user_account (email);
CREATE INDEX idx_progress_user_date ON progress_measurement (user_id, measured_at DESC);
CREATE INDEX idx_plan_user ON plan (user_id);
CREATE INDEX idx_plan_day_planid ON plan_day (plan_id, day_of_week);
