# Lazy_Bird Frontend

Modern React dashboard for managing the Lazy_Bird automation system.

## Tech Stack

- **React** 18+ with TypeScript
- **Vite** - Lightning-fast build tool and dev server
- **React Router** - Client-side routing with route-based forms
- **TanStack Query (React Query)** - Server state management
- **Tailwind CSS** - Utility-first CSS framework
- **Lucide React** - Beautiful icon library

## Getting Started

```bash
# Install dependencies
npm install

# Start development server (with HMR)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Lint code
npm run lint
```

The dev server will start at `http://localhost:5173` (or next available port).

## Project Structure

```
src/
├── App.tsx                   # Main app component with routes
├── main.tsx                  # Entry point with QueryClient
├── pages/                    # Route-based pages
│   ├── DashboardPage.tsx     # / - System overview
│   ├── ProjectsPage.tsx      # /projects - List projects
│   ├── ProjectFormPage.tsx   # /projects/add, /projects/:id/edit
│   ├── ServicesPage.tsx      # /services - List services
│   ├── ServiceFormPage.tsx   # /services/add, /services/:name/edit
│   ├── QueuePage.tsx         # /queue - View task queue
│   └── SettingsPage.tsx      # /settings - Configuration
├── components/               # Reusable components
│   ├── Layout.tsx            # Sidebar navigation wrapper
│   └── ProjectForm.tsx       # Project form component
├── hooks/                    # Custom React hooks
│   ├── useProjects.ts        # Project CRUD operations
│   └── useSystem.ts          # System status & control
├── lib/                      # Utilities
│   └── api.ts                # Axios API client
├── types/                    # TypeScript definitions
│   └── api.ts                # API response types
└── index.css                 # Global styles & Tailwind

## Architecture Decisions

### Route-Based Forms (Not Modals)

We use **dedicated route pages** for forms instead of modals:

**Before (Modal approach):**
- Click "Add Project" → Modal pops up
- URL stays `/projects`
- Can't bookmark the form
- Back button doesn't work

**After (Route-based):**
- Click "Add Project" → Navigate to `/projects/add`
- Full page for the form
- Bookmarkable URLs
- Back button works naturally

**Benefits:**
✅ More space for complex forms
✅ Bookmarkable & shareable URLs
✅ Browser navigation works (back/forward)
✅ Better mobile experience
✅ Clearer navigation state

### State Management

**TanStack Query (React Query):**
- Handles all server state (projects, services, queue, etc.)
- Automatic caching and background refetching
- Optimistic updates for better UX
- Automatic error handling and retries

**React Router:**
- Manages navigation state
- URL-based routing
- Route params (`:id`, `:name`)

**Local State (useState):**
- Form inputs
- UI toggles (dropdowns, etc.)
- Temporary data

### API Communication

All API calls go through `src/lib/api.ts`:

```typescript
import { api } from '../lib/api';

// GET request
const response = await api.get('/api/projects');

// POST request
await api.post('/api/projects', { name: 'My Project' });

// PUT request
await api.put('/api/projects/123', { enabled: false });

// DELETE request
await api.delete('/api/projects/123');
```

The API client automatically:
- Adds base URL (`http://localhost:5000`)
- Handles errors
- Sets proper headers

### Custom Hooks Pattern

All API logic is in custom hooks (not in components):

```typescript
// hooks/useProjects.ts
export function useProjects() {
  return useQuery({
    queryKey: ['projects'],
    queryFn: async () => {
      const response = await projectsApi.list();
      return response.data;
    },
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data) => {
      const response = await projectsApi.create(data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });
}
```

**Benefits:**
- Separation of concerns
- Easy to test
- Reusable across components
- Centralized API logic

## Routes

| Route | Component | Purpose |
|-------|-----------|---------|
| `/` | DashboardPage | System overview, status cards |
| `/projects` | ProjectsPage | List all projects |
| `/projects/add` | ProjectFormPage | Add new project |
| `/projects/:id/edit` | ProjectFormPage | Edit existing project |
| `/services` | ServicesPage | List systemd services |
| `/services/add` | ServiceFormPage | Create new service |
| `/services/:name/edit` | ServiceFormPage | Edit existing service |
| `/queue` | QueuePage | View task queue |
| `/settings` | SettingsPage | GitHub token, system settings |

## TypeScript Types

All API responses have proper TypeScript types in `src/types/api.ts`:

```typescript
export interface Project {
  id: string;
  name: string;
  type: string;
  path: string;
  repository: string;
  git_platform: 'github' | 'gitlab';
  test_command: string | null;
  build_command: string | null;
  enabled: boolean;
}

export interface ProjectCreate {
  name: string;
  type: string;
  path: string;
  repository: string;
  git_platform: 'github' | 'gitlab';
  test_command?: string;
  build_command?: string;
  enabled: boolean;
}
```

## Styling

### Tailwind CSS

We use **Tailwind CSS** with a custom configuration:

```typescript
// Dark mode support
<div className="bg-white dark:bg-gray-800 text-gray-900 dark:text-white">

// Responsive design
<div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

// Hover states
<button className="hover:bg-blue-700 transition-colors">
```

### Dark Mode

Dark mode is system-aware:
- Automatically detects OS preference
- Uses `dark:` prefix for dark mode styles
- Consistent across all pages

### Design Tokens

- Primary: Blue (`bg-blue-600`, `text-blue-600`)
- Success: Green (`bg-green-600`)
- Error: Red (`bg-red-600`)
- Spacing: Tailwind's spacing scale (4px base)
- Border radius: `rounded-md` (6px) for small, `rounded-lg` (8px) for large

## Development Tips

### Hot Module Replacement (HMR)

Vite provides instant HMR - just save and see changes immediately.

### React Query DevTools

Add React Query DevTools for debugging:

```bash
npm install @tanstack/react-query-devtools
```

```typescript
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';

<QueryClientProvider client={queryClient}>
  <App />
  <ReactQueryDevtools initialIsOpen={false} />
</QueryClientProvider>
```

### Type Safety

Always import types and use them:

```typescript
import type { Project } from '../types/api';

const [project, setProject] = useState<Project | null>(null);
```

### API Error Handling

Hooks automatically handle errors. Display them in UI:

```typescript
const { data, error } = useProjects();

if (error) {
  return <div>Error: {error.message}</div>;
}
```

## Building for Production

```bash
# Build optimized production bundle
npm run build

# Preview production build locally
npm run preview
```

The build output goes to `dist/` directory.

### Build Output

- **dist/index.html** - Entry HTML
- **dist/assets/** - JS, CSS, and assets
- All files are hashed for cache busting
- Minified and optimized

## Environment Variables

Create `.env` for custom configuration:

```env
# API base URL (default: http://localhost:5000)
VITE_API_URL=http://localhost:5000
```

Access in code:

```typescript
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';
```

## Common Tasks

### Adding a New Page

1. Create page component in `src/pages/`
2. Add route in `src/App.tsx`
3. Add navigation link in `src/components/Layout.tsx`

### Adding a New API Hook

1. Define types in `src/types/api.ts`
2. Add API endpoint in `src/lib/api.ts`
3. Create custom hook in `src/hooks/`
4. Use hook in component

### Debugging

- Check browser console for errors
- Use React DevTools
- Use React Query DevTools (if installed)
- Check Network tab for API calls

## Contributing

1. Follow TypeScript strict mode
2. Use functional components with hooks
3. Use Tailwind CSS for styling
4. Keep components small and focused
5. Extract logic to custom hooks
6. Add proper TypeScript types

## License

MIT License - Part of Lazy_Bird project
