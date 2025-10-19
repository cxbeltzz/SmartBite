CREATE SCHEMA IF NOT EXISTS "public";

CREATE  TABLE "public".activity_level ( 
	id                   smallint  NOT NULL GENERATED ALWAYS AS IDENTITY ,
	code                 varchar(32)  NOT NULL  ,
	description          text    ,
	CONSTRAINT activity_level_pkey PRIMARY KEY ( id ),
	CONSTRAINT activity_level_code_key UNIQUE ( code ) 
 );

CREATE  TABLE "public".dietary_restriction_type ( 
	id                   smallint  NOT NULL GENERATED ALWAYS AS IDENTITY ,
	code                 varchar(64)  NOT NULL  ,
	description          text    ,
	CONSTRAINT dietary_restriction_type_pkey PRIMARY KEY ( id ),
	CONSTRAINT dietary_restriction_type_code_key UNIQUE ( code ) 
 );

CREATE  TABLE "public".food_item ( 
	id                   bigint  NOT NULL GENERATED ALWAYS AS IDENTITY ,
	name                 varchar(256)  NOT NULL  ,
	description          text    ,
	created_at           timestamptz DEFAULT now() NOT NULL  ,
	CONSTRAINT food_item_pkey PRIMARY KEY ( id ),
	CONSTRAINT food_item_name_key UNIQUE ( name ) 
 );

CREATE INDEX idx_food_item_name ON "public".food_item  ( name );

CREATE  TABLE "public".gender_type ( 
	id                   smallint  NOT NULL GENERATED ALWAYS AS IDENTITY ,
	code                 varchar(16)  NOT NULL  ,
	description          text    ,
	CONSTRAINT gender_type_pkey PRIMARY KEY ( id ),
	CONSTRAINT gender_type_code_key UNIQUE ( code ) 
 );

CREATE  TABLE "public".meal_type ( 
	id                   smallint  NOT NULL GENERATED ALWAYS AS IDENTITY ,
	code                 varchar(32)  NOT NULL  ,
	description          text    ,
	CONSTRAINT meal_type_pkey PRIMARY KEY ( id ),
	CONSTRAINT meal_type_code_key UNIQUE ( code ) 
 );

CREATE  TABLE "public".objective_type ( 
	id                   smallint  NOT NULL GENERATED ALWAYS AS IDENTITY ,
	code                 varchar(32)  NOT NULL  ,
	description          text    ,
	CONSTRAINT objective_type_pkey PRIMARY KEY ( id ),
	CONSTRAINT objective_type_code_key UNIQUE ( code ) 
 );

CREATE  TABLE "public".recipe ( 
	id                   bigint  NOT NULL GENERATED ALWAYS AS IDENTITY ,
	title                varchar(300)  NOT NULL  ,
	description          text    ,
	servings             numeric(6,2) DEFAULT 1 NOT NULL  ,
	calories_per_serving numeric(8,2)    ,
	protein_g_per_serving numeric(8,2)    ,
	carbs_g_per_serving  numeric(8,2)    ,
	fats_g_per_serving   numeric(8,2)    ,
	saturatedfats_g_per_serving numeric(8,2)    ,
	cholesterol_g_per_serving numeric(8,2)    ,
	sodium_g_per_serving numeric(8,2)    ,
	fiber_g_per_serving  numeric(8,2)    ,
	sugar_g_per_serving  numeric(8,2)    ,
	CONSTRAINT recipe_pkey PRIMARY KEY ( id ),
	CONSTRAINT recipe_title_key UNIQUE ( title ) 
 );

CREATE INDEX idx_recipe_title ON "public".recipe  ( title );

CREATE  TABLE "public".recipe_ingredient ( 
	recipe_id            bigint  NOT NULL  ,
	food_item_id         bigint  NOT NULL  ,
	quantity             numeric(10,3)  NOT NULL  ,
	unit                 varchar(32)  NOT NULL  ,
	CONSTRAINT recipe_ingredient_pkey PRIMARY KEY ( recipe_id, food_item_id ),
	CONSTRAINT recipe_ingredient_food_item_id_fkey FOREIGN KEY ( food_item_id ) REFERENCES "public".food_item( id ) ON DELETE RESTRICT  ,
	CONSTRAINT recipe_ingredient_recipe_id_fkey FOREIGN KEY ( recipe_id ) REFERENCES "public".recipe( id ) ON DELETE CASCADE  
 );

CREATE  TABLE "public".user_account ( 
	id                   bigint  NOT NULL GENERATED ALWAYS AS IDENTITY ,
	email                varchar(320)  NOT NULL  ,
	full_name            varchar(200)    ,
	created_at           timestamptz DEFAULT now() NOT NULL  ,
	is_active            boolean DEFAULT true NOT NULL  ,
	CONSTRAINT user_account_pkey PRIMARY KEY ( id ),
	CONSTRAINT user_account_email_key UNIQUE ( email ) 
 );

CREATE INDEX idx_user_email ON "public".user_account  ( email );

CREATE  TABLE "public".user_activity ( 
	user_id              bigint  NOT NULL  ,
	activity_level_id    smallint  NOT NULL  ,
	effective_from       date DEFAULT CURRENT_DATE NOT NULL  ,
	effective_to         date    ,
	CONSTRAINT user_activity_pkey PRIMARY KEY ( user_id, effective_from ),
	CONSTRAINT user_activity_activity_level_id_fkey FOREIGN KEY ( activity_level_id ) REFERENCES "public".activity_level( id )   ,
	CONSTRAINT user_activity_user_id_fkey FOREIGN KEY ( user_id ) REFERENCES "public".user_account( id ) ON DELETE CASCADE  
 );

CREATE  TABLE "public".user_dietary_restriction ( 
	user_id              bigint  NOT NULL  ,
	restriction_id       smallint  NOT NULL  ,
	noted_at             timestamptz DEFAULT now() NOT NULL  ,
	CONSTRAINT user_dietary_restriction_pkey PRIMARY KEY ( user_id, restriction_id ),
	CONSTRAINT user_dietary_restriction_restriction_id_fkey FOREIGN KEY ( restriction_id ) REFERENCES "public".dietary_restriction_type( id ) ON DELETE RESTRICT  ,
	CONSTRAINT user_dietary_restriction_user_id_fkey FOREIGN KEY ( user_id ) REFERENCES "public".user_account( id ) ON DELETE CASCADE  
 );

CREATE  TABLE "public".user_food_preference ( 
	user_id              bigint  NOT NULL  ,
	food_item_id         bigint  NOT NULL  ,
	preference           smallint  NOT NULL  ,
	noted_at             timestamptz DEFAULT now() NOT NULL  ,
	CONSTRAINT user_food_preference_pkey PRIMARY KEY ( user_id, food_item_id ),
	CONSTRAINT user_food_preference_food_item_id_fkey FOREIGN KEY ( food_item_id ) REFERENCES "public".food_item( id ) ON DELETE RESTRICT  ,
	CONSTRAINT user_food_preference_user_id_fkey FOREIGN KEY ( user_id ) REFERENCES "public".user_account( id ) ON DELETE CASCADE  
 );

CREATE  TABLE "public".user_objective ( 
	user_id              bigint  NOT NULL  ,
	objective_type_id    smallint  NOT NULL  ,
	target_weight_kg     numeric(6,2)    ,
	start_date           date DEFAULT CURRENT_DATE NOT NULL  ,
	target_date          date    ,
	created_at           timestamptz DEFAULT now() NOT NULL  ,
	updated_at           timestamptz DEFAULT now() NOT NULL  ,
	CONSTRAINT user_objective_pkey PRIMARY KEY ( user_id ),
	CONSTRAINT user_objective_objective_type_id_fkey FOREIGN KEY ( objective_type_id ) REFERENCES "public".objective_type( id )   ,
	CONSTRAINT user_objective_user_id_fkey FOREIGN KEY ( user_id ) REFERENCES "public".user_account( id ) ON DELETE CASCADE  
 );

CREATE  TABLE "public".user_profile ( 
	user_id              bigint  NOT NULL  ,
	birth_date           date    ,
	gender_id            smallint    ,
	height_cm            numeric(5,2)    ,
	created_at           timestamptz DEFAULT now() NOT NULL  ,
	updated_at           timestamptz DEFAULT now() NOT NULL  ,
	CONSTRAINT user_profile_pkey PRIMARY KEY ( user_id ),
	CONSTRAINT user_profile_gender_id_fkey FOREIGN KEY ( gender_id ) REFERENCES "public".gender_type( id )   ,
	CONSTRAINT user_profile_user_id_fkey FOREIGN KEY ( user_id ) REFERENCES "public".user_account( id ) ON DELETE CASCADE  
 );

CREATE  TABLE "public".auth_credential ( 
	id                   bigint  NOT NULL GENERATED ALWAYS AS IDENTITY ,
	user_id              bigint  NOT NULL  ,
	password_hash        text  NOT NULL  ,
	salt                 text    ,
	created_at           timestamptz DEFAULT now() NOT NULL  ,
	last_login_at        timestamptz    ,
	CONSTRAINT auth_credential_pkey PRIMARY KEY ( id ),
	CONSTRAINT auth_credential_user_id_key UNIQUE ( user_id ) ,
	CONSTRAINT auth_credential_user_id_fkey FOREIGN KEY ( user_id ) REFERENCES "public".user_account( id ) ON DELETE CASCADE  
 );

CREATE  TABLE "public".plan ( 
	id                   bigint  NOT NULL GENERATED ALWAYS AS IDENTITY ,
	user_id              bigint  NOT NULL  ,
	title                varchar(200)    ,
	created_at           timestamptz DEFAULT now() NOT NULL  ,
	start_date           date    ,
	end_date             date    ,
	total_calories_per_day numeric(9,2)    ,
	total_protein_g_per_day numeric(9,2)    ,
	notes                text    ,
	CONSTRAINT plan_pkey PRIMARY KEY ( id ),
	CONSTRAINT plan_user_id_fkey FOREIGN KEY ( user_id ) REFERENCES "public".user_account( id ) ON DELETE CASCADE  
 );

CREATE INDEX idx_plan_user ON "public".plan  ( user_id );

CREATE  TABLE "public".plan_day ( 
	id                   bigint  NOT NULL GENERATED ALWAYS AS IDENTITY ,
	plan_id              bigint  NOT NULL  ,
	day_of_week          smallint  NOT NULL  ,
	CONSTRAINT plan_day_pkey PRIMARY KEY ( id ),
	CONSTRAINT plan_day_plan_id_day_of_week_key UNIQUE ( plan_id, day_of_week ) ,
	CONSTRAINT plan_day_plan_id_fkey FOREIGN KEY ( plan_id ) REFERENCES "public".plan( id ) ON DELETE CASCADE  
 );

ALTER TABLE "public".plan_day ADD CONSTRAINT plan_day_day_of_week_check CHECK ( ((day_of_week >= 1) AND (day_of_week <= 7)) );

CREATE INDEX idx_plan_day_planid ON "public".plan_day  ( plan_id, day_of_week );

CREATE  TABLE "public".plan_meal ( 
	id                   bigint  NOT NULL GENERATED ALWAYS AS IDENTITY ,
	plan_day_id          bigint  NOT NULL  ,
	meal_type_id         smallint  NOT NULL  ,
	meal_order           smallint  NOT NULL  ,
	notes                text    ,
	CONSTRAINT plan_meal_pkey PRIMARY KEY ( id ),
	CONSTRAINT plan_meal_plan_day_id_meal_type_id_meal_order_key UNIQUE ( plan_day_id, meal_type_id, meal_order ) ,
	CONSTRAINT plan_meal_meal_type_id_fkey FOREIGN KEY ( meal_type_id ) REFERENCES "public".meal_type( id )   ,
	CONSTRAINT plan_meal_plan_day_id_fkey FOREIGN KEY ( plan_day_id ) REFERENCES "public".plan_day( id ) ON DELETE CASCADE  
 );

CREATE  TABLE "public".plan_meal_recipe ( 
	plan_meal_id         bigint  NOT NULL  ,
	recipe_id            bigint  NOT NULL  ,
	servings             numeric(6,2) DEFAULT 1 NOT NULL  ,
	CONSTRAINT plan_meal_recipe_pkey PRIMARY KEY ( plan_meal_id, recipe_id ),
	CONSTRAINT plan_meal_recipe_plan_meal_id_fkey FOREIGN KEY ( plan_meal_id ) REFERENCES "public".plan_meal( id ) ON DELETE CASCADE  ,
	CONSTRAINT plan_meal_recipe_recipe_id_fkey FOREIGN KEY ( recipe_id ) REFERENCES "public".recipe( id ) ON DELETE RESTRICT  
 );

CREATE  TABLE "public".progress_measurement ( 
	id                   bigint  NOT NULL GENERATED ALWAYS AS IDENTITY ,
	user_id              bigint  NOT NULL  ,
	weight_kg            numeric(6,2)    ,
	body_fat_percent     numeric(5,2)    ,
	notes                text    ,
	CONSTRAINT progress_measurement_pkey PRIMARY KEY ( id ),
	CONSTRAINT progress_measurement_user_id_fkey FOREIGN KEY ( user_id ) REFERENCES "public".user_account( id ) ON DELETE CASCADE  
 );

CREATE INDEX idx_progress_user_date ON "public".progress_measurement  ( user_id );

CREATE  TABLE "public".user_saved_plan ( 
	user_id              bigint  NOT NULL  ,
	plan_id              bigint  NOT NULL  ,
	saved_at             timestamptz DEFAULT now() NOT NULL  ,
	is_favorite          boolean DEFAULT false NOT NULL  ,
	CONSTRAINT user_saved_plan_pkey PRIMARY KEY ( user_id, plan_id ),
	CONSTRAINT user_saved_plan_plan_id_fkey FOREIGN KEY ( plan_id ) REFERENCES "public".plan( id ) ON DELETE CASCADE  ,
	CONSTRAINT user_saved_plan_user_id_fkey FOREIGN KEY ( user_id ) REFERENCES "public".user_account( id ) ON DELETE CASCADE  
 );


