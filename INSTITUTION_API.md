# Institution Timeline API Documentation

## Get Student's Institution Timeline

**Endpoint:** `GET /institutions/timeline/my-institution`

**Authentication:** Required (Bearer token in Authorization header)

**Role:** Student only

**Description:**
Returns the logged-in student's institution details (name, location, description, logo, website) plus all school-scoped posts for that institution.

### Request Headers
```
Authorization: Bearer <campustalk_access_token>
```

### Response Example
```json
{
  "institution": {
    "id": "unilag",
    "institution_name": "University of Lagos",
    "institution_description": "The University of Lagos (UNILAG) is a federal university founded in 1962...",
    "institution_website": "https://unilag.edu.ng",
    "institution_location": "Akoka, Yaba, Lagos State, Nigeria",
    "institution_profile_picture": "https://i.pinimg.com/736x/7c/0e/fe/7c0efec92682d80048147b2e73d3c4d2.jpg",
    "institution_email": "info@unilag.edu.ng",
    "students_count": 5,
    "posts_count": 2
  },
  "posts": [
    {
      "id": "post-001",
      "author_id": "user-123",
      "content": "Welcome students to the University of Lagos campus! 🎓 Check the electric bus service to move around campus.",
      "post_type": "post",
      "privacy": "school_only",
      "school_scope": "University of Lagos",
      "created_at": "2025-11-17T10:30:00Z"
    },
    {
      "id": "post-002",
      "author_id": "user-123",
      "content": "Final exam schedules are now available on the student portal.",
      "post_type": "post",
      "privacy": "school_only",
      "school_scope": "University of Lagos",
      "created_at": "2025-11-17T09:15:00Z"
    }
  ]
}
```

### Error Responses

**401 Unauthorized** - No valid authentication token
```json
{
  "detail": "You are not authenticated. Please login to continue"
}
```

**403 Forbidden** - User is not a student
```json
{
  "detail": "Only students can view institution timelines"
}
```

**404 Not Found** - Student profile or institution not found
```json
{
  "detail": "Student profile or institution not found"
}
```

---

## Create Institution Post (Admin Only)

**Endpoint:** `POST /institutions/{institution_id}/posts`

**Authentication:** Required (Bearer token)

**Role:** Institution admin only

**Description:**
Create a new post for the institution. If `mirror_to_general=true`, the post appears on the general feed as well. Otherwise, it's visible only to students of that institution.

### Request Body
```json
{
  "content": "Welcome message for students",
  "post_type": "post",  // or "reel"
  "mirror_to_general": false  // if true, post appears on general feed too
}
```

### Query Parameters
- `content` (string, required) - Post content
- `post_type` (string, optional, default="post") - "post" or "reel"
- `mirror_to_general` (boolean, optional, default=false) - Mirror to general feed

### Response (201 Created)
```json
{
  "id": "post-001",
  "author_id": "user-123",
  "content": "Welcome message for students",
  "post_type": "post",
  "privacy": "school_only",  // "school_only" if mirror_to_general=false
  "school_scope": "University of Lagos",
  "created_at": "2025-11-17T10:30:00Z"
}
```

---

## Frontend Integration

### Example React Hook Usage
```jsx
import { useEffect, useState } from 'react';

export function InstitutionTimeline() {
  const [institution, setInstitution] = useState(null);
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const token = localStorage.getItem('campustalk_access_token');

  useEffect(() => {
    const fetchTimeline = async () => {
      try {
        const res = await fetch('/institutions/timeline/my-institution', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        if (res.ok) {
          const data = await res.json();
          setInstitution(data.institution);
          setPosts(data.posts);
        }
      } catch (err) {
        console.error('Failed to fetch timeline:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchTimeline();
  }, [token]);

  if (loading) return <div>Loading...</div>;

  return (
    <div>
      {institution && (
        <header>
          <img src={institution.institution_profile_picture} alt="logo" />
          <h1>{institution.institution_name}</h1>
          <p>{institution.institution_description}</p>
          <p>📍 {institution.institution_location}</p>
          <p>Students: {institution.students_count} | Posts: {institution.posts_count}</p>
        </header>
      )}
      
      <section className="posts">
        {posts.map(post => (
          <article key={post.id}>
            <p>{post.content}</p>
            <small>{new Date(post.created_at).toLocaleString()}</small>
          </article>
        ))}
      </section>
    </div>
  );
}
```

---

## Database Schema Alignment

The endpoint pulls data from:
- **Institution** table: id, institution_name, institution_description, institution_website, institution_location, institution_profile_picture, institution_email
- **StudentProfile** table: Links logged-in user to their institution
- **Post** table: Posts with `school_scope` matching the institution name and `privacy="school_only"`

All models and schemas are properly aligned as of this update.
