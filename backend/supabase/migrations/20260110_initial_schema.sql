-- 1. Create Enums
DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('parent', 'kid');
    CREATE TYPE intent_type AS ENUM ('giveaway', 'sell', 'share');
    CREATE TYPE reservation_status AS ENUM ('pending', 'active', 'completed', 'cancelled');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 2. Create Categories table
CREATE TABLE IF NOT EXISTS category (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Create Profiles table (linked to Auth)
CREATE TABLE IF NOT EXISTS profile (
    id UUID PRIMARY KEY REFERENCES auth.users ON DELETE CASCADE,
    username TEXT UNIQUE,
    full_name TEXT,
    avatar_url TEXT,
    role user_role DEFAULT 'parent',
    parent_id UUID REFERENCES profile(id) ON DELETE SET NULL,
    credits INTEGER DEFAULT 0,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Create Books table
CREATE TABLE IF NOT EXISTS book (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    description TEXT,
    isbn TEXT,
    published_year INTEGER,
    pages INTEGER,
    price DECIMAL(12,2),
    stock_count INTEGER DEFAULT 1,
    intent intent_type DEFAULT 'share',
    is_active BOOLEAN DEFAULT TRUE,
    owner_id UUID REFERENCES profile(id) ON DELETE CASCADE,
    category_id INTEGER REFERENCES category(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. Create Reservations table
CREATE TABLE IF NOT EXISTS reservation (
    id SERIAL PRIMARY KEY,
    book_id INTEGER REFERENCES book(id) ON DELETE CASCADE,
    borrower_id UUID REFERENCES profile(id) ON DELETE CASCADE,
    status reservation_status DEFAULT 'pending',
    start_date TIMESTAMP WITH TIME ZONE NOT NULL,
    end_date TIMESTAMP WITH TIME ZONE NOT NULL,
    credits_used INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 6. Create Credits History
CREATE TABLE IF NOT EXISTS creditshistory (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES profile(id) ON DELETE CASCADE,
    amount INTEGER NOT NULL,
    type TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 7. Create Feed Items
CREATE TABLE IF NOT EXISTS feeditem (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES profile(id) ON DELETE CASCADE,
    action_type TEXT NOT NULL,
    content TEXT NOT NULL,
    feed_metadata JSONB DEFAULT '{}',
    is_public BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 8. Enable Realtime
BEGIN;
  DROP PUBLICATION IF EXISTS supabase_realtime;
  CREATE PUBLICATION supabase_realtime FOR TABLE book, reservation, feeditem, category;
COMMIT;

-- 9. Performance Optimization: Indexes
CREATE INDEX IF NOT EXISTS idx_book_title ON book USING GIN (to_tsvector('english', title));
CREATE INDEX IF NOT EXISTS idx_book_author ON book USING GIN (to_tsvector('english', author));
CREATE INDEX IF NOT EXISTS idx_book_category ON book(category_id);
CREATE INDEX IF NOT EXISTS idx_reservation_book ON reservation(book_id);

-- 10. Row Level Security (RLS)
ALTER TABLE book ENABLE ROW LEVEL SECURITY;
ALTER TABLE profile ENABLE ROW LEVEL SECURITY;
ALTER TABLE reservation ENABLE ROW LEVEL SECURITY;
ALTER TABLE category ENABLE ROW LEVEL SECURITY;
ALTER TABLE creditshistory ENABLE ROW LEVEL SECURITY;
ALTER TABLE feeditem ENABLE ROW LEVEL SECURITY;

-- Category Policies
CREATE POLICY "Public Read Access" ON category FOR SELECT USING (true);

-- Profile Policies
CREATE POLICY "Public Read Access" ON profile FOR SELECT USING (true);
CREATE POLICY "Users Control Own Profile" ON profile FOR ALL TO authenticated USING (auth.uid() = id);

-- Book Policies
CREATE POLICY "Public Read Access" ON book FOR SELECT USING (is_active = TRUE);
CREATE POLICY "Users Control Own Books" ON book 
    FOR ALL 
    TO authenticated 
    USING (auth.uid() = owner_id)
    WITH CHECK (auth.uid() = owner_id);

-- Reservation Policies
CREATE POLICY "Users Control Own Reservations" ON reservation
    FOR ALL
    TO authenticated
    USING (auth.uid() = borrower_id)
    WITH CHECK (auth.uid() = borrower_id);

-- Credit History Policies
CREATE POLICY "Users View Own Credits" ON creditshistory
    FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

-- Feed Item Policies
CREATE POLICY "Public View Public Feed" ON feeditem
    FOR SELECT
    USING (is_public = TRUE);

CREATE POLICY "Users Control Own Feed" ON feeditem
    FOR ALL
    TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- 11. Automatic Feed Triggers
CREATE OR REPLACE FUNCTION public.handle_new_book() 
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.feeditem (user_id, action_type, content, feed_metadata)
    VALUES (NEW.owner_id, 'book_added', 'Added a new book: ' || NEW.title, jsonb_build_object('book_id', NEW.id, 'title', NEW.title));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DO $$ BEGIN
    CREATE TRIGGER on_book_added
        AFTER INSERT ON public.book
        FOR EACH ROW EXECUTE FUNCTION public.handle_new_book();
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

CREATE OR REPLACE FUNCTION public.handle_new_reservation() 
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.feeditem (user_id, action_type, content, feed_metadata)
    VALUES (NEW.borrower_id, 'reservation_created', 'Reserved a book', jsonb_build_object('reservation_id', NEW.id, 'book_id', NEW.book_id));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DO $$ BEGIN
    CREATE TRIGGER on_reservation_added
        AFTER INSERT ON public.reservation
        FOR EACH ROW EXECUTE FUNCTION public.handle_new_reservation();
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 12. Automatic Profile Creation on Signup
CREATE OR REPLACE FUNCTION public.handle_new_user() 
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profile (id, username, full_name, avatar_url)
    VALUES (
        NEW.id, 
        COALESCE(NEW.raw_user_meta_data->>'username', NEW.email), 
        NEW.raw_user_meta_data->>'full_name', 
        NEW.raw_user_meta_data->>'avatar_url'
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DO $$ BEGIN
    CREATE TRIGGER on_auth_user_created
        AFTER INSERT ON auth.users
        FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;
