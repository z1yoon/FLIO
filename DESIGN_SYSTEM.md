# FLIO Design System

This document defines the consistent design patterns used throughout the FLIO dating app.

## Colors

### Background
- **Primary Background**: Ocean gradient 
  ```
  colors: ['#2E7D7A', '#4FD1C7', '#7EDDD9', '#B0E7E4']
  locations: [0, 0.4, 0.7, 1]
  ```
- **Fallback Background**: `#2E7D7A` (teal)

### Buttons
- **Primary Button Gradient**: `['#00FFC8', '#00D4AA']`
  - Direction: Horizontal (`start: { x: 0, y: 0 }, end: { x: 1, y: 0 }`)

### Text Colors
- **Primary Text**: `#FFFFFF` (white)
- **Button Text**: `#FFFFFF` (white)
- **Placeholder Text**: `rgba(255, 255, 255, 0.4)` or `rgba(255, 255, 255, 0.5)`

## Components

### Primary Button (Standard)
```tsx
<TouchableOpacity
  style={styles.primaryButton}
  onPress={handleAction}
  activeOpacity={0.8}
>
  <LinearGradient
    colors={['#00FFC8', '#00D4AA']}
    start={{ x: 0, y: 0 }}
    end={{ x: 1, y: 0 }}
    style={styles.gradientButton}
  >
    <Text style={styles.primaryButtonText}>Button Text</Text>
  </LinearGradient>
</TouchableOpacity>

// Styles
const styles = StyleSheet.create({
  primaryButton: {
    width: '100%',
    marginTop: 40,
  },
  gradientButton: {
    paddingVertical: 18,
    borderRadius: 30,
    alignItems: 'center',
    justifyContent: 'center',
  },
  primaryButtonText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#FFFFFF',
  },
});
```

### Primary Button with Icon
```tsx
<TouchableOpacity
  style={styles.primaryButton}
  onPress={handleAction}
  activeOpacity={0.8}
>
  <LinearGradient
    colors={['#00FFC8', '#00D4AA']}
    start={{ x: 0, y: 0 }}
    end={{ x: 1, y: 0 }}
    style={styles.gradientButtonWithIcon}
  >
    <Text style={styles.primaryButtonText}>Button Text</Text>
    <Ionicons name="arrow-forward" size={20} color="#FFFFFF" />
  </LinearGradient>
</TouchableOpacity>

// Styles
const styles = StyleSheet.create({
  gradientButtonWithIcon: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 18,
    borderRadius: 30,
    gap: 8,
  },
});
```

### Background Container
```tsx
<View style={styles.container}>
  <LinearGradient
    colors={['#2E7D7A', '#4FD1C7', '#7EDDD9', '#B0E7E4']}
    locations={[0, 0.4, 0.7, 1]}
    style={styles.backgroundGradient}
  />
  
  {/* Content */}
</View>

// Styles
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#2E7D7A',
  },
  backgroundGradient: {
    ...StyleSheet.absoluteFillObject,
  },
});
```

### Input Field
```tsx
<View style={styles.inputContainer}>
  <Ionicons name="icon-name" size={20} color="rgba(255, 255, 255, 0.7)" />
  <TextInput
    style={styles.input}
    placeholder="Placeholder text"
    placeholderTextColor="rgba(255, 255, 255, 0.4)"
    value={value}
    onChangeText={setValue}
  />
</View>

// Styles
const styles = StyleSheet.create({
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    borderRadius: 16,
    paddingHorizontal: 16,
    height: 56,
    gap: 12,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.2)',
  },
  input: {
    flex: 1,
    fontSize: 16,
    color: '#FFFFFF',
  },
});
```

## Typography

### Headings
- **H1 (Page Title)**: `fontSize: 28, fontWeight: '700', color: '#FFFFFF'`
- **H2 (Section Title)**: `fontSize: 24, fontWeight: '700', color: '#FFFFFF'`
- **H3 (Subtitle)**: `fontSize: 18, fontWeight: '600', color: '#FFFFFF'`

### Body Text
- **Primary**: `fontSize: 16, color: '#FFFFFF'`
- **Secondary**: `fontSize: 14, color: 'rgba(255, 255, 255, 0.8)'`
- **Caption**: `fontSize: 12, color: 'rgba(255, 255, 255, 0.7)'`

### Button Text
- **Primary Button**: `fontSize: 18, fontWeight: '600', color: '#FFFFFF'`
- **Secondary Button**: `fontSize: 16, fontWeight: '600', color: '#FFFFFF'`

## Spacing

### Margins
- **Screen Padding**: `24px` horizontal
- **Component Spacing**: `16px`, `24px`, `32px`, `40px`
- **Button Spacing**: `16px` between buttons

### Border Radius
- **Buttons**: `30px` (highly rounded)
- **Input Fields**: `16px`
- **Cards/Containers**: `20px`
- **Small Elements**: `8px`

## Shadows & Effects

### Button Shadows
```tsx
shadowColor: 'rgba(0, 0, 0, 0.2)',
shadowOffset: { width: 0, height: 4 },
shadowOpacity: 0.3,
shadowRadius: 8,
elevation: 8,
```

## Animation

### Touch Feedback
- **activeOpacity**: `0.8` for all touchable elements
- **Animation Duration**: `200-600ms` for UI transitions
- **Easing**: `Easing.out(Easing.cubic)` for smooth animations

## Usage Rules

1. **Always use white text** on FLIO gradient buttons
2. **Always use the ocean gradient background** for consistency
3. **Use the standard button component** for all primary actions
4. **Maintain 30px border radius** for all buttons
5. **Use consistent spacing** (24px screen padding, 40px button margins)
6. **Apply activeOpacity={0.8}** to all touchable elements

## Import Requirements

```tsx
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
```

---

**Note**: This design system should be followed for all new components and screens to maintain visual consistency across the FLIO app.