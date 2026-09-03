/**
 * Shared helpers for turning a post's `category` frontmatter string into a
 * stable URL slug, so the homepage, post pages and /category/* pages all agree.
 */
export function categorySlug(category: string): string {
  return category
    .toLowerCase()
    .replace(/&/g, ' and ')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

export function categoryPath(category: string): string {
  return `/category/${categorySlug(category)}/`;
}
