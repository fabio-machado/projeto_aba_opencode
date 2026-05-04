-- Migration 006: Gerador de Rotinas
-- Tables: pictogram_categories, pictograms, routines, routine_items

-- 1. pictogram_categories
CREATE TABLE IF NOT EXISTS public.pictogram_categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    display_order INTEGER NOT NULL DEFAULT 0
);

ALTER TABLE public.pictogram_categories ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Pictogram categories are viewable by everyone" 
    ON public.pictogram_categories FOR SELECT 
    USING (true);

-- 2. pictograms
CREATE TABLE IF NOT EXISTS public.pictograms (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    category_id UUID NOT NULL REFERENCES public.pictogram_categories(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    image_url TEXT NOT NULL
);

ALTER TABLE public.pictograms ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Pictograms are viewable by everyone" 
    ON public.pictograms FOR SELECT 
    USING (true);

-- 3. routines
CREATE TABLE IF NOT EXISTS public.routines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    parent_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    title VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_routines_parent_id ON public.routines(parent_id);

ALTER TABLE public.routines ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Routines are viewable by owner" 
    ON public.routines FOR SELECT 
    USING (parent_id = auth.uid());

CREATE POLICY "Routines are insertable by owner" 
    ON public.routines FOR INSERT 
    WITH CHECK (parent_id = auth.uid());

CREATE POLICY "Routines are updatable by owner" 
    ON public.routines FOR UPDATE 
    USING (parent_id = auth.uid())
    WITH CHECK (parent_id = auth.uid());

CREATE POLICY "Routines are deletable by owner" 
    ON public.routines FOR DELETE 
    USING (parent_id = auth.uid());

-- Trigger para updated_at (reaproveitando function se existir ou criando)
CREATE OR REPLACE FUNCTION set_current_timestamp_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS set_routines_updated_at ON public.routines;
CREATE TRIGGER set_routines_updated_at
    BEFORE UPDATE ON public.routines
    FOR EACH ROW
    EXECUTE FUNCTION set_current_timestamp_updated_at();

-- 4. routine_items
CREATE TABLE IF NOT EXISTS public.routine_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    routine_id UUID NOT NULL REFERENCES public.routines(id) ON DELETE CASCADE,
    pictogram_id UUID NOT NULL REFERENCES public.pictograms(id) ON DELETE CASCADE,
    order_position INTEGER NOT NULL CHECK (order_position >= 0)
);

CREATE INDEX IF NOT EXISTS idx_routine_items_routine ON public.routine_items(routine_id, order_position);

ALTER TABLE public.routine_items ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Routine items are viewable by routine owner" 
    ON public.routine_items FOR SELECT 
    USING (EXISTS (
        SELECT 1 FROM public.routines 
        WHERE routines.id = routine_items.routine_id 
        AND routines.parent_id = auth.uid()
    ));

CREATE POLICY "Routine items are insertable by routine owner" 
    ON public.routine_items FOR INSERT 
    WITH CHECK (EXISTS (
        SELECT 1 FROM public.routines 
        WHERE routines.id = routine_items.routine_id 
        AND routines.parent_id = auth.uid()
    ));

CREATE POLICY "Routine items are updatable by routine owner" 
    ON public.routine_items FOR UPDATE 
    USING (EXISTS (
        SELECT 1 FROM public.routines 
        WHERE routines.id = routine_items.routine_id 
        AND routines.parent_id = auth.uid()
    ))
    WITH CHECK (EXISTS (
        SELECT 1 FROM public.routines 
        WHERE routines.id = routine_items.routine_id 
        AND routines.parent_id = auth.uid()
    ));

CREATE POLICY "Routine items are deletable by routine owner" 
    ON public.routine_items FOR DELETE 
    USING (EXISTS (
        SELECT 1 FROM public.routines 
        WHERE routines.id = routine_items.routine_id 
        AND routines.parent_id = auth.uid()
    ));

-- Seed: Categorias iniciais
INSERT INTO public.pictogram_categories (id, name, display_order)
VALUES 
    ('83296068-d055-4673-8db2-0943efbf44a1', 'Higiene', 1),
    ('4b0253f9-71c1-4b19-94d7-ea760b76ee7b', 'Alimentação', 2),
    ('715b706c-84ce-472e-bdf1-b1e42f9b877f', 'Escola', 3),
    ('f25ef046-dfb5-474c-8bb2-53b759bbfa97', 'Lazer', 4),
    ('b9d2e185-9333-47cb-b4eb-28682894178f', 'Terapia', 5),
    ('c5c8edec-1300-47b2-a4f6-8c4ed945ccb1', 'Sono', 6),
    ('b9c6f2df-50f9-43c2-aa2e-40e8371306eb', 'Outros', 7)
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, display_order = EXCLUDED.display_order;
