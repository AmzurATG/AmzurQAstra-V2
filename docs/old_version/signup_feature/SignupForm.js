import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FaEye, FaEyeSlash,FaChevronDown  } from 'react-icons/fa';
import { countries } from '../utils/countryData';
import validTLDsData from '../utils/tlds.json';
import applogo from '../assets/images/logo.png';
import bgImage from '../assets/images/login-bg.png';
import routes from '../utils/routes/routes';
import Select from 'react-select';

// Create a Set for efficient TLD lookup
const validTLDs = new Set(validTLDsData.tlds);

const SignupForm = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    companyName: '',
    email: '',
    countryCode: 'IN', // Default to India country code
    phoneNumber: '',
    password: '',
    confirmPassword: ''
  });
  
  const [errors, setErrors] = useState({});
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const validateName = (name, fieldName) => {
    // Check length
    if (name.length === 0) {
      return { isValid: false, message: `${fieldName} is required` };
    }
    if (name.length > 50) {
      return { isValid: false, message: `${fieldName} must not exceed 50 characters` };
    }
    
    // Check allowed characters (alphabets, space, hyphen only)
    const nameRegex = /^[a-zA-Z\s-]+$/;
    if (!nameRegex.test(name)) {
      return { isValid: false, message: `${fieldName} can only contain letters, spaces, and hyphens` };
    }
    
    return { isValid: true, message: '' };
  };

  const validateEmail = (email, companyName = '') => {
    // Check max length (RFC standard)
    if (email.length > 254) {
      return { isValid: false, message: 'Email address is too long (max 254 characters)' };
    }
    
    // Check for spaces
    if (email.includes(' ')) {
      return { isValid: false, message: 'Email address cannot contain spaces' };
    }
    
    
    // Enhanced email format validation with proper domain structure
    // Pattern explanation:
    // - Local part: alphanumeric, dots, hyphens, underscores (not starting/ending with dot)
    // - Domain: alphanumeric with hyphens, must have valid TLD (2-6 chars)
    const emailRegex = /^[a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?@[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}$/;
    
    if (!emailRegex.test(email)) {
      return { isValid: false, message: 'Please enter a valid email address with a proper domain' };
    }
    
    // Validate domain structure more strictly
    const emailParts = email.split('@');
    if (emailParts.length !== 2) {
      return { isValid: false, message: 'Please enter a valid email address' };
    }
    
    const domain = emailParts[1].toLowerCase();
    const domainParts = domain.split('.');
    
    // Domain must have at least 2 parts (e.g., company.com)
    if (domainParts.length < 2) {
      return { isValid: false, message: 'Email domain must include a valid top-level domain (e.g., .com, .org)' };
    }
    
    // Check TLD (last part) against valid TLDs
    const tld = domainParts[domainParts.length - 1];
    
    if (!validTLDs.has(tld)) {
      return { isValid: false, message: 'Please enter a valid email with a recognized domain extension (e.g., .com, .org, .net)' };
    }
    
    // Check each domain part is valid (not empty, alphanumeric with hyphens)
    for (const part of domainParts) {
      if (part.length === 0 || !/^[a-zA-Z0-9-]+$/.test(part)) {
        return { isValid: false, message: 'Email domain contains invalid characters' };
      }
      // Domain parts shouldn't start or end with hyphen
      if (part.startsWith('-') || part.endsWith('-')) {
        return { isValid: false, message: 'Email domain format is invalid' };
      }
    }
    
    // Business email validation - check for common free email providers and mailinator.com
    const freeEmailProviders = [
      'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 
      'aol.com', 'icloud.com', 'mail.com', 'protonmail.com',
      'zoho.com', 'yandex.com', 'gmx.com', 'live.com'
    ];
    const blockedDisposableDomains = ['mailinator.com'];
    if (blockedDisposableDomains.includes(domain)) {
      return { isValid: false, message: 'Disposable email addresses like mailinator.com are not allowed' };
    }
    if (freeEmailProviders.includes(domain)) {
      return { isValid: false, message: 'Please use a business email address (you@company.com)' };
    }
    
    // Validate that email domain matches company name
    if (companyName && companyName.trim()) {
      // Normalize company name: remove special characters, spaces, convert to lowercase
      const normalizedCompany = companyName
        .toLowerCase()
        .replace(/[^a-z0-9]/g, '');
      
      // Extract the main domain name (without TLD)
      const domainName = domainParts.slice(0, -1).join('').toLowerCase();
      
      // Check if domain contains the company name or vice versa
      // This allows for variations like "test" matching "test.com" or "testinc.com"
      if (!domainName.includes(normalizedCompany) && !normalizedCompany.includes(domainName)) {
        return { 
          isValid: false, 
          message: `Business email domain should match your company name. Expected domain like ${normalizedCompany}.com` 
        };
      }
    }
    
    return { isValid: true, message: '' };
  };

  const validatePhoneNumber = (phoneNumber, countryCode) => {
    if (!phoneNumber || !phoneNumber.trim()) {
      return { isValid: true, message: '' }; // Optional field
    }

    // Remove any non-digit characters
    const digitsOnly = phoneNumber.replace(/\D/g, '');
    
    // Find the selected country by country code (e.g., 'IN', 'US', 'CA')
    const selectedCountry = countries.find(country => country.code === countryCode);
    if (!selectedCountry) {
      return { isValid: false, message: 'Invalid country code' };
    }

    const requiredDigits = selectedCountry.phone_digits;

    // Check exact digit count for the country
    if (digitsOnly.length !== requiredDigits) {
      return { isValid: false, message: `Phone number must be exactly ${requiredDigits} digits for ${selectedCountry.name}` };
    }
    
    // Check if only digits
    const digitRegex = /^\d+$/;
    if (!digitRegex.test(digitsOnly)) {
      return { isValid: false, message: 'Phone number can only contain digits' };
    }
    
    return { isValid: true, message: '' };
  };

  const validateCompanyName = (companyName) => {
    // Check length
    if (companyName.length === 0) {
      return { isValid: false, message: 'Company Name is required' };
    }
    if (companyName.length < 2) {
      return { isValid: false, message: 'Company name must be at least 2 characters' };
    }
    if (companyName.length > 100) {
      return { isValid: false, message: 'Company name must not exceed 100 characters' };
    }
    
    // Check allowed characters (alphanumeric, space, hyphen, period, ampersand, comma, apostrophe, parentheses, exclamation, colon, semicolon, slash, question mark, quotes, em dash, en dash, underscore)
    const companyNameRegex = /^[a-zA-Z0-9\s\-\.&,\'()!:;\/\?"—–_]+$/;
    if (!companyNameRegex.test(companyName)) {
      return { isValid: false, message: 'Company name contains invalid characters' };
    }
    
    return { isValid: true, message: '' };
  };

  const validatePassword = (password) => {
    const errors = [];
    
    // Check length
    if (password.length < 8) {
      errors.push('be at least 8 characters long');
    }
    if (password.length > 64) {
      errors.push('not exceed 64 characters');
    }
    
    // Check for whitespace
    if (/\s/.test(password)) {
      errors.push('not contain whitespace');
    }
    
    // Check for uppercase letter
    if (!/[A-Z]/.test(password)) {
      errors.push('contain at least one uppercase letter');
    }
    
    // Check for lowercase letter
    if (!/[a-z]/.test(password)) {
      errors.push('contain at least one lowercase letter');
    }
    
    // Check for number
    if (!/[0-9]/.test(password)) {
      errors.push('contain at least one number');
    }
    
    // Check for special character
    if (!/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)) {
      errors.push('contain at least one special character (!@#$%^&* etc.)');
    }
    
    // Return dynamic error message based on missing requirements
    if (errors.length > 0) {
      return { 
        isValid: false, 
        message: `Password must ${errors.join(', ')}.` 
      };
    }
    
    return { isValid: true, message: '' };
  };

  const validateForm = () => {
    const newErrors = {};
    
    // Validate first name
    const firstNameValidation = validateName(formData.firstName.trim(), 'First Name');
    if (!firstNameValidation.isValid) {
      newErrors.firstName = firstNameValidation.message;
    }
    
    // Validate last name
    const lastNameValidation = validateName(formData.lastName.trim(), 'Last Name');
    if (!lastNameValidation.isValid) {
      newErrors.lastName = lastNameValidation.message;
    }
    
    // Validate company name
    const companyNameValidation = validateCompanyName(formData.companyName.trim());
    if (!companyNameValidation.isValid) {
      newErrors.companyName = companyNameValidation.message;
    }
    
    // Validate email
    if (!formData.email.trim()) {
      newErrors.email = 'Business Email is required';
    } else {
      const emailValidation = validateEmail(formData.email.trim(), formData.companyName.trim());
      if (!emailValidation.isValid) {
        newErrors.email = emailValidation.message;
      }
    }

    // Validate phone number only if provided
    if (formData.phoneNumber && formData.phoneNumber.trim()) {
      const phoneValidation = validatePhoneNumber(formData.phoneNumber, formData.countryCode);
      if (!phoneValidation.isValid) {
        newErrors.phoneNumber = phoneValidation.message;
      }
    }

    // Validate password
    if (!formData.password) {
      newErrors.password = 'Password is required';
    } else {
      const passwordValidation = validatePassword(formData.password);
      if (!passwordValidation.isValid) {
        newErrors.password = passwordValidation.message;
      }
    }

    // Validate confirm password
    if (!formData.confirmPassword) {
      newErrors.confirmPassword = 'Confirm Password is required';
    } else if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    const newFormData = {
      ...formData,
      [name]: value
    };
    setFormData(newFormData);
    
    // Clear error when user starts typing
    if (errors[name]) {
      setErrors({
        ...errors,
        [name]: ''
      });
    }
    
    // Instant validation for confirm password field
    if (name === 'confirmPassword') {
      if (value && formData.password && value !== formData.password) {
        setErrors({
          ...errors,
          confirmPassword: 'Passwords do not match'
        });
      } else if (value === formData.password) {
        setErrors({
          ...errors,
          confirmPassword: ''
        });
      }
    }
    
    // Also check confirm password when password field changes
    if (name === 'password') {
      // Clear password error if the new password is valid
      const passwordValidation = validatePassword(value);
      const newErrors = { ...errors };
      
      if (passwordValidation.isValid) {
        newErrors.password = '';
      }
      
      // Check confirm password match if it exists
      if (formData.confirmPassword) {
        if (value !== formData.confirmPassword) {
          newErrors.confirmPassword = 'Passwords do not match';
        } else {
          newErrors.confirmPassword = '';
        }
      }
      
      setErrors(newErrors);
    }
    
    // Re-validate email when company name changes
    if (name === 'companyName' && formData.email && formData.email.trim()) {
      const validation = validateEmail(formData.email.trim(), value.trim());
      if (!validation.isValid) {
        setErrors({
          ...errors,
          email: validation.message
        });
      } else if (errors.email && errors.email.includes('company name')) {
        // Clear email error if it was related to company name mismatch
        setErrors({
          ...errors,
          email: ''
        });
      }
    }
    
    // Re-validate email when email changes (to check company name match)
    if (name === 'email' && formData.companyName && formData.companyName.trim()) {
      const validation = validateEmail(value.trim(), formData.companyName.trim());
      if (!validation.isValid) {
        setErrors({
          ...errors,
          email: validation.message
        });
      }
    }
  };
  
  const handleCountryCodeChange = (selectedOption) => {
    const newFormData = {
      ...formData,
      countryCode: selectedOption.value // This will now be country code like 'IN', 'US', 'CA'
    };
    setFormData(newFormData);
    
    // Re-validate phone number if it exists when country changes
    if (formData.phoneNumber && formData.phoneNumber.trim()) {
      const phoneValidation = validatePhoneNumber(formData.phoneNumber, selectedOption.value);
      if (!phoneValidation.isValid) {
        setErrors({
          ...errors,
          phoneNumber: phoneValidation.message
        });
      } else {
        // Clear phone number error if now valid
        setErrors({
          ...errors,
          phoneNumber: ''
        });
      }
    }
  };
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }
    
    // Clear any previous form errors
    setErrors(prev => ({...prev, form: ''}));
    setIsLoading(true);
    
    try {
      // Check if email is already registered
      const checkEmailResponse = await fetch('http://localhost:8000/check-email', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: formData.email
        })
      });
      
      const checkEmailData = await checkEmailResponse.json();
      
      if (!checkEmailResponse.ok) {
        throw new Error(checkEmailData.detail || 'Failed to check email');
      }
      
      // Check if the email already exists from response data
      if (checkEmailData.exists) {
        setErrors({
          ...errors,
          email: 'This email address is already registered'
        });
        setIsLoading(false);
        return; // Stop the form submission here
      }
      
      // Format user data for API - use snake_case for backend API
      const userData = {
        first_name: formData.firstName,
        last_name: formData.lastName,
        company_name: formData.companyName,
        email: formData.email,
        country_code: selectedCountry?.dial_code || '+91', // Send the dial code to backend
        phone_number: formData.phoneNumber.trim() || '0000000000', // Send default value if empty
        password: formData.password,
        confirm_password: formData.confirmPassword
      };
      
      // Navigate to security questions page with the user data
      navigate(routes.securityQuestions, { state: { userData } });
    } catch (error) {
      console.error('Signup error:', error);
      
      let errorMessage = error.message;
      try {
        if (error.message.includes('[object Object]')) {
          errorMessage = 'Invalid form data. Please check all fields and try again.';
        }
      } catch (e) {
        // Keep original error message if parsing fails
      }
      
      setErrors({
        ...errors,
        form: errorMessage || 'An error occurred during sign up'
      });
    } finally {
      setIsLoading(false);
    }
  };
  
  const selectedCountry = countries.find(country => country.code === formData.countryCode);
  
  // Prepare country options for react-select - use country code as unique value
  const countryOptions = countries.map(country => ({
    value: country.code, // Use country code (e.g., 'IN', 'US', 'CA') as unique identifier
    label: `${country.code} ${country.dial_code} - ${country.name}`,
    shortLabel: `${country.code} ${country.dial_code}`,
    name: country.name,
    dialCode: country.dial_code
  }));
  
  return (
    <div 
      className="h-screen bg-cover bg-center bg-no-repeat flex items-center justify-center p-4 overflow-y-auto"
      style={{ backgroundImage: `url(${bgImage})` }}
    >
      <div className="w-full max-w-md  pt-[48px]">
        {/* Logo outside and centered above the card */}
        <div className="flex justify-center mb-6">
          <img src={applogo} alt="QAstra" className="h-8 w-auto"/>
        </div>
        
        {/* Card */}
        <div className="bg-white/90 backdrop-blur-sm rounded-2xl shadow-lg p-2">
          <div className="text-center px-6 pt-4 pb-4">
            <div className="text-2xl sm:text-lg md:text-2xl lg:text-2xl font-semibold text-gray-900">Sign Up</div>
          </div>
       <div className="px-6 pb-6 pt-5">
      {errors.form && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-1.5 rounded-md mb-4 text-sm">
          {errors.form}
        </div>
      )}
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mb-4">
          <div>            
            <label className="block sm:text-sm md:text-md lg:text-base font-medium text-gray-900 mb-1.5" htmlFor="firstName">
              First Name <span style={{ color: 'var(--destructive)' }}>*</span>
            </label>
            <input
              className={`w-full px-3 py-2 border rounded-md bg-white text-gray-900 sm:text-sm md:text-md lg:text-base font-normal placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-tileBorder focus:border-tileBg transition-all duration-200 ${
                errors.firstName ? 'border-red-300 focus:ring-red-500 focus:border-red-500' : 'border-gray-300 hover:border-gray-200'
              }`}
              id="firstName"
              name="firstName"
              type="text"
              maxLength="50"
              value={formData.firstName}
              onChange={handleChange}
              placeholder="Enter First Name"
            />
            {errors.firstName && <p className="text-red-600 text-sm mt-1">{errors.firstName}</p>}
          </div>
          
          <div>            
            <label className="block sm:text-sm md:text-md lg:text-base font-medium text-gray-900 mb-1.5" htmlFor="lastName">
              Last Name <span style={{ color: 'var(--destructive)' }}>*</span>
            </label>
            <input
              className={`w-full px-3 py-2 border rounded-md bg-white font-normal text-gray-900 sm:text-sm md:text-md lg:text-base placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-tileBorder focus:border-tileBg transition-all duration-200 ${
                errors.lastName ? 'border-red-300 focus:ring-red-500 focus:border-red-500' : 'border-gray-300 hover:border-gray-200'
              }`}
              id="lastName"
              name="lastName"
              type="text"
              maxLength="50"
              value={formData.lastName}
              onChange={handleChange}
              placeholder="Enter Last Name"
            />
            {errors.lastName && <p className="text-red-600 text-sm mt-1">{errors.lastName}</p>}
          </div>
        </div>
        
        <div> 
            <label className="block sm:text-sm md:text-md lg:text-base font-medium text-gray-900 mb-1.5" htmlFor="companyName">
            Company Name <span style={{ color: 'var(--destructive)' }}>*</span>
          </label>
          <input
            className={`w-full px-3 py-2 border rounded-md bg-white text-gray-900 sm:text-sm md:text-md lg:text-base placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-tileBorder focus:border-tileBg transition-all duration-200 ${
              errors.companyName ? 'border-red-300 focus:ring-red-500 focus:border-red-500' : 'border-gray-300 hover:border-gray-200'
            }`}
            id="companyName"
            name="companyName"
            type="text"
            maxLength="100"
            value={formData.companyName}
            onChange={handleChange}
            placeholder="Enter Company Name"
          />
          {errors.companyName && <p className="text-red-600 text-sm mt-1">{errors.companyName}</p>}
        </div>
        
        <div> 
           <label className="block sm:text-sm md:text-md lg:text-base font-medium text-gray-900 mb-1.5" htmlFor="email">
            Business Email <span style={{ color: 'var(--destructive)' }}>*</span>
          </label>
          <input
            className={`w-full px-3 py-2 border rounded-md bg-white text-gray-900 sm:text-sm md:text-md lg:text-base placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-tileBorder focus:border-tileBg transition-all duration-200 ${
              errors.email ? 'border-red-300 focus:ring-red-500 focus:border-red-500' : 'border-gray-300 hover:border-gray-200'
            }`}
            id="email"
            name="email"
            type="text"
            maxLength="254"
            value={formData.email}
            onChange={handleChange}
            placeholder="your.email@company.com"
            autoComplete="email"
          />
          {errors.email && <p className="text-red-600 text-sm mt-1">{errors.email}</p>}
        </div>
        
        <div>
          <label className="block sm:text-sm md:text-md lg:text-base font-medium text-gray-900 mb-1.5" htmlFor="phoneNumber">
            Phone Number
          </label>
          <div className="flex gap-2">
            <Select
              options={countryOptions}
              value={countryOptions.find(option => option.value === formData.countryCode)}
              onChange={handleCountryCodeChange}
              className="react-select-container border border-gray-300 rounded-md"
              classNamePrefix="react-select"
              formatOptionLabel={(option, { context }) => {
                return context === 'value' ? option.shortLabel : option.label;
              }}
              styles={{
                container: (provided) => ({
                  ...provided,
                  width: '120px',
                  minWidth: '120px'
                }),
                control: (provided, state) => ({
                  ...provided,
                  backgroundColor: 'white',
                  padding: '2px 4px',
                  fontSize: '14px',
                  border:'none',
                  '&:hover': {
                    borderColor: '#e5e7eb'
                  },
                  boxShadow: state.isFocused ? '0 0 0 1px var(--tileBorder)' : 'none',
                  '&:focus-within': {
                    
                    outline: 'none'
                  }
                }),
                menu: (provided) => ({
                  ...provided,
                  maxHeight: '200px',
                  width: '300px',
                  minWidth: '300px',
                  zIndex: 9999
                }),
                menuList: (provided) => ({
                  ...provided,
                  maxHeight: '180px'
                }),
                option: (provided, state) => ({
                  ...provided,
                  fontSize: '14px',
                  backgroundColor: state.isSelected ? 'var(--primary)' : state.isFocused ? '#f3f4f6' : 'white',
                  color: state.isSelected ? 'white' : '#1f2937',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  '&:hover': {
                    backgroundColor: state.isSelected ? 'var(--primary)' : '#f3f4f6'
                  }
                }),
                singleValue: (provided) => ({
                  ...provided,
                  fontSize: '14px',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis'
                })
              }}
              placeholder="Select country"
              isSearchable={true}
              maxMenuHeight={200}
            />
            
            <input
              className={`w-full px-3 py-2 border rounded-md bg-white text-gray-900 sm:text-sm md:text-md lg:text-base placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-tileBorder focus:border-tileBg transition-all duration-200 ${
                  errors.phoneNumber ? 'border-red-300 focus:ring-red-500 focus:border-red-500' : 'border-gray-300 hover:border-gray-200'
                }`}
              id="phoneNumber"
              name="phoneNumber"
              type="tel"
              maxLength={selectedCountry?.phone_digits || 15}
              placeholder="Enter Phone Number"
              value={formData.phoneNumber}
              onChange={e => {
                // Only allow digits and restrict to country's max length
                const digitsOnly = e.target.value.replace(/\D/g, '');
                const maxDigits = selectedCountry?.phone_digits || 15;
                const limitedDigits = digitsOnly.slice(0, maxDigits);
                handleChange({
                  target: {
                    name: 'phoneNumber',
                    value: limitedDigits
                  }
                });
              }}
            />
          </div>
          {errors.phoneNumber && <p className="text-red-600 text-sm mt-1">{errors.phoneNumber}</p>}
        </div>
        
        <div>
          <label className="block sm:text-sm md:text-md lg:text-base font-medium text-gray-900 mb-1.5" htmlFor="password">
            Password <span style={{ color: 'var(--destructive)' }}>*</span>
          </label>
          <div className="relative">
            <input
              className={`w-full px-3 py-2 border rounded-md bg-white text-gray-900 sm:text-sm md:text-md lg:text-base placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-tileBorder focus:border-tileBg pr-10 transition-all duration-200 ${
                errors.password ? 'border-red-300 focus:ring-red-500 focus:border-red-500' : 'border-gray-300 hover:border-gray-200'
              }`}
              id="password"
              name="password"
              type={showPassword ? "text" : "password"}
              maxLength="64"
              value={formData.password}
              onChange={handleChange}
              placeholder="Enter Password"
            />
            <button
              type="button"
              className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors focus:outline-none"
              onClick={() => setShowPassword(!showPassword)}
            >
              {showPassword ? <FaEyeSlash /> : <FaEye />}
            </button>
          </div>
          {errors.password && <p className="text-red-600 text-sm mt-1">{errors.password}</p>}
        </div>
        
        <div>
          <label className="block sm:text-sm md:text-md lg:text-base font-medium text-gray-900 mb-1.5" htmlFor="confirmPassword">
            Confirm Password <span style={{ color: 'var(--destructive)' }}>*</span>
          </label>
          <div className="relative">
            <input
              className={`w-full px-3 py-2 border rounded-md bg-white text-gray-900 sm:text-sm md:text-md lg:text-base placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-tileBorder focus:border-tileBg pr-10 transition-all duration-200 ${
                errors.confirmPassword ? 'border-red-300 focus:ring-red-500 focus:border-red-500' : 'border-gray-300 hover:border-gray-200'
              }`}
              id="confirmPassword"
              name="confirmPassword"
              type={showConfirmPassword ? "text" : "password"}
              maxLength="64"
              value={formData.confirmPassword}
              onChange={handleChange}
              placeholder="Confirm Password"
            />
            <button
              type="button"
              className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors focus:outline-none"
              onClick={() => setShowConfirmPassword(!showConfirmPassword)}
            >
              {showConfirmPassword ? <FaEyeSlash /> : <FaEye />}
            </button>
          </div>
          {errors.confirmPassword && <p className="text-red-600 text-sm mt-1">{errors.confirmPassword}</p>}
        </div>
        
        <button
          type="submit"
          disabled={isLoading}
          className={`w-full text-white font-medium py-2 px-2 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 transition-all duration-200 mt-6 text-md ${
            isLoading ? 'opacity-50 cursor-not-allowed' : ''
          }`}
          style={{ backgroundColor: 'var(--primary)' }}
        >
          {isLoading ? 'Processing...' : 'Sign Up'}
        </button>
      </form>
        <div className="text-center sm:text-sm md:text-md lg:text-base text-gray-600 font-normal mt-4">        
          Already have an account?{' '}
          <button 
            onClick={() => navigate(routes.login)}
            className="font-medium transition-colors"
            style={{ color: 'var(--primary)' }}
          >
            Sign In
          </button>
        
      </div>
      </div>
      </div>
      </div>
    </div>
  );
};

export default SignupForm;